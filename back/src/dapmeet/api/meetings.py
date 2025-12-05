from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload
from sqlalchemy import select, desc
from sqlalchemy.exc import SQLAlchemyError, DBAPIError, IntegrityError
from dapmeet.models.user import User
from dapmeet.models.meeting import Meeting
from dapmeet.models.segment import TranscriptSegment
from dapmeet.services.auth import get_current_user
from dapmeet.core.deps import get_async_db
from dapmeet.services.meetings import MeetingService
from dapmeet.services.subscription import SubscriptionService
from dapmeet.schemas.meetings import MeetingCreate, MeetingOut, MeetingPatch, MeetingOutList, MeetingListResponse
from dapmeet.schemas.segment import TranscriptSegmentCreate, TranscriptSegmentOut
from dapmeet.schemas.decoding import (
    ParticipantsSyncRequest, ParticipantsResponse, RawTranscriptRequest, 
    RawTranscriptResponse, DecodedData, ParticipantMapping
)
from dapmeet.services.mapping import mapping_service
from dapmeet.services.decoder import decoder_service
from dapmeet.services.message_cache import message_cache_service
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=MeetingListResponse)
async def get_meetings(
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_async_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's meetings with pagination.
    
    Args:
        limit: Maximum number of meetings to return (default 50, max 100)
        offset: Number of meetings to skip (default 0)
    """
    # Enforce reasonable limits
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    
    meeting_service = MeetingService(db)
    
    # Get meetings and total count sequentially (can't use same session concurrently)
    meetings = await meeting_service.get_meetings_with_speakers(
        user_id=user.id, 
        limit=limit, 
        offset=offset
    )
    total = await meeting_service.get_meetings_count(user_id=user.id)
    
    return MeetingListResponse(
        meetings=meetings,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(meetings)) < total
    )
    
@router.post("/", response_model=MeetingOut)
async def create_or_get_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
):
    meeting_service = MeetingService(db)
    
    # Get subscription plan and save it with the meeting
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_or_create_subscription(user.id)
    
    meeting = await meeting_service.get_or_create_meeting(meeting_data=data, user=user)
    
    # Save subscription plan if not already set
    if not meeting.subscription_plan:
        meeting.subscription_plan = subscription.plan.value
        await db.commit()

    # Re-load with segments eagerly fetched so Pydantic won't trigger IO later
    stmt = (
        select(Meeting)
        .options(selectinload(Meeting.segments))  # <- key line
        .where(Meeting.unique_session_id == meeting.unique_session_id)
    )
    result = await db.execute(stmt)
    meeting_loaded = result.scalar_one()
    return meeting_loaded


# Специфичные маршруты должны быть ПЕРЕД общим маршрутом /{meeting_id}
# чтобы FastAPI правильно их обрабатывал

@router.post("/{meeting_id}/participants", status_code=200)
async def sync_participants(
    meeting_id: str,
    request: ParticipantsSyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Синхронизация маппинга участников от расширения.
    Сохраняет соответствие device_id -> имя участника с вариантами для поиска.
    """
    # Логируем ВСЕ входящие запросы на синхронизацию
    log_msg_start = (
        f"[MAPPING-SYNC-START] Meeting {meeting_id}: Received sync request - "
        f"user_id={user.id}, "
        f"participants_count={len(request.participants)}, "
        f"session_id={request.session_id}, "
        f"space_id={request.space_id}"
    )
    logger.info(log_msg_start)
    print(log_msg_start)  # Дублируем в stdout
    
    # Логируем детали каждого участника
    for idx, participant in enumerate(request.participants):
        log_msg_participant = (
            f"[MAPPING-SYNC-PARTICIPANT] Meeting {meeting_id}: Participant {idx+1}/{len(request.participants)} - "
            f"device_id='{participant.device_id}', "
            f"name='{participant.name}', "
            f"variants={participant.variants}"
        )
        logger.info(log_msg_participant)
        print(log_msg_participant)
    
    try:
        # Проверяем, что встреча существует
        # Используем поиск через like, так как встреча может иметь суффикс даты
        base_session_id = f"{meeting_id}-{user.id}"
        result = await db.execute(
            select(Meeting)
            .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
            .order_by(desc(Meeting.created_at))
            .limit(1)
        )
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        session_id = meeting.unique_session_id
        
        # Логируем начало синхронизации
        logger.info(
            f"[MAPPING-SYNC] Meeting {meeting_id}: Starting sync - "
            f"participants_count={len(request.participants)}, "
            f"session_id={request.session_id}, space_id={request.space_id}"
        )
        
        # Сохраняем маппинг для каждого участника
        for participant in request.participants:
            mapping_service.save_mapping(
                meeting_id=meeting_id,
                device_id=participant.device_id,
                name=participant.name,
                variants=participant.variants
            )
        
        # Логируем завершение синхронизации
        logger.info(
            f"[MAPPING-SYNC] Meeting {meeting_id}: Completed sync - "
            f"synced {len(request.participants)} participants"
        )
        
        return {"status": "ok", "participants_count": len(request.participants)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing participants for meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync participants: {str(e)}")


@router.get("/{meeting_id}/participants", response_model=ParticipantsResponse)
async def get_participants(
    meeting_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получение текущего маппинга участников (для отладки).
    """
    try:
        # Логируем запрос маппинга
        logger.info(
            f"[MAPPING-GET-ENDPOINT] Meeting {meeting_id}: Retrieving participants mapping"
        )
        # Проверяем, что встреча существует
        # Используем поиск через like, так как встреча может иметь суффикс даты
        base_session_id = f"{meeting_id}-{user.id}"
        result = await db.execute(
            select(Meeting)
            .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
            .order_by(desc(Meeting.created_at))
            .limit(1)
        )
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Получаем маппинг
        mapping = mapping_service.get_mapping(meeting_id)
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Participants mapping not found")
        
        # Преобразуем в список ParticipantMapping
        participants = []
        last_updated = None
        for device_id, data in mapping.items():
            participants.append(ParticipantMapping(
                device_id=device_id,
                name=data["name"],
                variants=data["variants"]
            ))
            if last_updated is None or data["updated_at"] > last_updated:
                last_updated = data["updated_at"]
        
        return ParticipantsResponse(
            participants=participants,
            last_updated=last_updated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting participants for meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get participants: {str(e)}")


@router.delete("/{meeting_id}/participants", status_code=204)
async def clear_participants(
    meeting_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Очистка маппинга участников при завершении встречи.
    """
    try:
        # Проверяем, что встреча существует
        # Используем поиск через like, так как встреча может иметь суффикс даты
        base_session_id = f"{meeting_id}-{user.id}"
        result = await db.execute(
            select(Meeting)
            .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
            .order_by(desc(Meeting.created_at))
            .limit(1)
        )
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Очищаем маппинг
        mapping_service.clear_mapping(meeting_id)
        
        logger.info(f"Cleared participants mapping for meeting {meeting_id}")
        
        return Response(status_code=204)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing participants for meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear participants: {str(e)}")


@router.get("/{meeting_id}/info", response_model=MeetingOutList)
async def get_meeting_info(
    meeting_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает последнюю актуальную встречу (< 24 часов).
    Если встречи нет или последняя >= 24 часов назад — 404.
    """
    base_session_id = f"{meeting_id}-{user.id}"
    now_utc = datetime.now(timezone.utc)

    # Берём самую свежую встречу для base_session_id (с учётом возможных суффиксов даты)
    result = await db.execute(
        select(Meeting)
        .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
        .order_by(desc(Meeting.created_at))
        .limit(1)
    )
    last_meeting = result.scalar_one_or_none()

    if not last_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Проверяем "моложе ли 24 часов"
    age = now_utc - last_meeting.created_at
    if age >= timedelta(hours=24):
        # Старше/равно 24ч — считаем неактуальной, просим клиента создать новую
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Актуальная — возвращаем
    return last_meeting


@router.post("/{meeting_id}/segments", 
    response_model=TranscriptSegmentOut, 
    status_code=201,)
async def add_segment(
    meeting_id: str,
    seg_in: TranscriptSegmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Add a transcript segment to a meeting.
    Includes proper error handling to ensure database connections are released.
    """
    try:
        # Проверяем, что встреча существует и принадлежит текущему пользователю
        meeting_service = MeetingService(db)
        meeting = await meeting_service.get_meeting_by_session_id(session_id=meeting_id, user_id=user.id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        session_id = meeting.unique_session_id
        
        # Создаем новый сегмент с переданными данными
        segment = TranscriptSegment(
            session_id=session_id,
            google_meet_user_id=seg_in.google_meet_user_id,
            speaker_username=seg_in.username,
            timestamp=seg_in.timestamp,
            text=seg_in.text,
            version=seg_in.ver,
            message_id=seg_in.mess_id
        )
        
        db.add(segment)
        await db.commit()
        await db.refresh(segment)
        return segment
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) as-is
        raise
    except DBAPIError as e:
        # Database connection/pool errors
        await db.rollback()
        logger.error(f"Database connection error in add_segment for meeting {meeting_id}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail="Database connection error. Please try again."
        )
    except SQLAlchemyError as e:
        # Other database errors
        await db.rollback()
        logger.error(f"Database error in add_segment for meeting {meeting_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to save transcript segment"
        )
    except Exception as e:
        # Unexpected errors
        await db.rollback()
        logger.error(f"Unexpected error in add_segment for meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred"
        )


@router.post("/{meeting_id}/raw-transcript", response_model=RawTranscriptResponse)
async def decode_raw_transcript(
    meeting_id: str,
    request: RawTranscriptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получение RAW данных транскрипта для декодирования.
    Декодирует base64, распаковывает gzip, извлекает данные из protobuf,
    ищет имя участника в маппинге и сохраняет сегмент в БД.
    """
    try:
        # Проверяем, что встреча существует
        # Используем поиск через like, так как встреча может иметь суффикс даты
        base_session_id = f"{meeting_id}-{user.id}"
        result = await db.execute(
            select(Meeting)
            .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
            .order_by(desc(Meeting.created_at))
            .limit(1)
        )
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        session_id = meeting.unique_session_id
        
        # Логируем сырые данные (base64)
        raw_data_length = len(request.raw_data) if request.raw_data else 0
        raw_data_preview = request.raw_data[:100] if request.raw_data else ""
        logger.info(
            f"[RAW-TRANSCRIPT] Meeting {meeting_id}: "
            f"raw_data_length={raw_data_length}, "
            f"raw_data_preview={raw_data_preview}..., "
            f"label={request.label}, "
            f"session_id={request.session_id}"
        )
        
        # Декодируем RAW данные
        try:
            # Декодируем base64 чтобы получить байты
            import base64
            try:
                raw_bytes = base64.b64decode(request.raw_data)
                
                # Логируем полностью все байты в одной строке
                bytes_list = list(raw_bytes)
                log_msg = (
                    f"[DECODED-BYTES-FULL] Meeting {meeting_id}: "
                    f"bytes_length={len(raw_bytes)}, "
                    f"bytes_full={bytes_list}"
                )
                logger.info(log_msg)
                print(log_msg)  # Дублируем в stdout для гарантии
                
                # Также логируем краткую информацию
                hex_string = raw_bytes.hex()
                logger.info(
                    f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Decoded raw bytes - "
                    f"length={len(raw_bytes)}, "
                    f"hex_first_200={hex_string[:200]}..., "
                    f"bytes_list_first_100={bytes_list[:100]}"
                )
                
            except Exception as e:
                logger.warning(f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Failed to decode base64 for logging: {str(e)}")
            
            decoded_data = decoder_service.decode_raw_data(request.raw_data)
            
            # Логируем ПОЛНОСТЬЮ декодированные данные (для анализа)
            log_msg_full = (
                f"[DECODED-FULL] Meeting {meeting_id}: "
                f"device_id_FULL='{decoded_data.get('device_id', '')}', "
                f"text_FULL='{decoded_data.get('text', '')}', "
                f"message_id={decoded_data.get('message_id')}, "
                f"version={decoded_data.get('version')}, "
                f"lang_id={decoded_data.get('lang_id')}"
            )
            logger.info(log_msg_full)
            print(log_msg_full)  # Дублируем в stdout для гарантии
            
            # Также логируем краткую информацию
            logger.info(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Decoded data - "
                f"device_id_length={len(decoded_data.get('device_id', ''))}, "
                f"device_id_preview={decoded_data.get('device_id', '')[:50] if decoded_data.get('device_id') else ''}..., "
                f"message_id={decoded_data.get('message_id')}, "
                f"version={decoded_data.get('version')}, "
                f"lang_id={decoded_data.get('lang_id')}, "
                f"text_length={len(decoded_data.get('text', ''))}, "
                f"text_preview={decoded_data.get('text', '')[:100] if decoded_data.get('text') else ''}..."
            )
            
        except ValueError as e:
            logger.error(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Decoding error - {str(e)}, "
                f"raw_data_length={raw_data_length}"
            )
            return RawTranscriptResponse(
                success=False,
                decoded=None,
                saved=False,
                error=f"Failed to decode: {str(e)}"
            )
        
        # Валидация декодированных данных
        logger.debug(
            f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Full decoded_data - {decoded_data}"
        )
        
        # Если device_id пустой или содержит только служебные символы, но текст есть,
        # генерируем fallback device_id из session_id или используем пустую строку
        device_id_raw = decoded_data.get("device_id", "")
        # Очищаем device_id от служебных символов
        device_id_clean = device_id_raw.strip('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c').strip()
        
        if not device_id_clean and decoded_data.get("text"):
            # Генерируем fallback device_id на основе message_id для уникальности
            logger.warning(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: device_id is empty/malformed but text exists. "
                f"raw_device_id={repr(device_id_raw)}, "
                f"text={decoded_data.get('text')[:50]}..."
            )
            # Используем message_id для уникальности fallback device_id
            # Это предотвратит дубликаты в БД при одинаковых timestamp
            message_id_for_fallback = decoded_data.get("message_id")
            if message_id_for_fallback:
                fallback_device_id = f"fallback_msg_{message_id_for_fallback}"
            else:
                # Если нет message_id, используем session_id или timestamp
                session_suffix = request.session_id[:8] if request.session_id else meeting_id[:8]
                timestamp_hash = hash(str(request.timestamp)) % 1000000 if request.timestamp else 0
                fallback_device_id = f"fallback_{session_suffix}_{timestamp_hash}"
            
            decoded_data["device_id"] = fallback_device_id
            logger.info(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Using fallback device_id={fallback_device_id}"
            )
        
        if not decoded_data.get("device_id") or not decoded_data.get("text"):
            logger.warning(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Invalid decoded data - "
                f"device_id={decoded_data.get('device_id')}, "
                f"text={decoded_data.get('text')}, "
                f"full_data={decoded_data}"
            )
            return RawTranscriptResponse(
                success=False,
                decoded=None,
                saved=False,
                error="Decoded data missing device_id or text"
            )
        
        # Ищем имя участника в маппинге
        device_id = decoded_data["device_id"]
        
        # Логируем попытку поиска в маппинге с информацией о доступных маппингах
        if meeting_id in mapping_service._mapping:
            available_keys = list(mapping_service._mapping[meeting_id].keys())
            index_keys_sample = list(mapping_service._index.get(meeting_id, {}).keys())[:10]
            logger.info(
                f"[MAPPING-LOOKUP] Meeting {meeting_id}: Looking up name for device_id='{device_id}', "
                f"available_device_ids_in_mapping={available_keys}, "
                f"index_keys_sample={index_keys_sample}, "
                f"total_mappings={len(mapping_service._mapping[meeting_id])}"
            )
        else:
            available_meetings = list(mapping_service._mapping.keys())
            logger.warning(
                f"[MAPPING-LOOKUP] Meeting {meeting_id}: No mapping exists for this meeting, "
                f"device_id='{device_id}', "
                f"available_meetings={available_meetings}"
            )
        
        # Валидация и очистка device_id - удаляем бинарные/непечатаемые символы и обрезаем до лимита
        if device_id:
            original_length = len(device_id)
            
            # Удаляем непечатаемые символы (кроме допустимых)
            device_id_clean = ''.join(c for c in device_id if c.isprintable() or c in '/\\-_@.')
            
            # Обрезаем до 500 символов (лимит БД) - ВАЖНО: обрезаем ПОСЛЕ очистки
            device_id = device_id_clean[:500] if len(device_id_clean) > 500 else device_id_clean
            
            # Если device_id содержит текст сообщения (видно из логов), обрезаем до первого неправильного символа
            # Обычно device_id это путь вида "spaces/.../devices/...", если есть текст - это ошибка извлечения
            if '/' in device_id:
                # Пробуем найти конец правильного device_id (до первого неожиданного текста)
                # device_id должен заканчиваться на число или ID, а не на текст сообщения
                parts = device_id.split('/')
                if len(parts) >= 3 and 'devices' in parts:
                    # Находим индекс 'devices'
                    devices_idx = parts.index('devices')
                    if devices_idx + 1 < len(parts):
                        device_num = parts[devices_idx + 1]
                        # Если после номера устройства идет текст - обрезаем
                        if len(device_num) > 50 or not device_num.replace('/', '').replace('_', '').replace('-', '').replace('.', '').isalnum():
                            # Возможно это не номер устройства, а мусор
                            pass
                        else:
                            # Проверяем, нет ли текста после устройства
                            remaining = '/'.join(parts[devices_idx + 2:])
                            if remaining and len(remaining) > 10:
                                # Есть текст после устройства - обрезаем до устройства
                                device_id = '/'.join(parts[:devices_idx + 2])
                                logger.warning(
                                    f"[RAW-TRANSCRIPT] Meeting {meeting_id}: device_id contained text, trimmed to: {device_id}"
                                )
            
            # Финальная обрезка до лимита
            device_id = device_id[:500] if len(device_id) > 500 else device_id
            
            if len(device_id) != original_length:
                logger.warning(
                    f"[RAW-TRANSCRIPT] Meeting {meeting_id}: device_id cleaned/truncated from {original_length} to {len(device_id)} chars"
                )
        
        username = mapping_service.find_name_by_device_id(meeting_id, device_id)
        
        if not username:
            # Используем "Unknown" с последними 4 символами
            username = mapping_service.get_unknown_name(device_id)
            logger.warning(
                f"[MAPPING-LOOKUP] Meeting {meeting_id}: Participant not found in mapping - "
                f"device_id='{device_id[:100]}...', using fallback name='{username}'"
            )
        else:
            logger.info(
                f"[MAPPING-LOOKUP] Meeting {meeting_id}: Found participant name - "
                f"device_id='{device_id[:100]}...', name='{username}'"
            )
        
        # Валидация username - обрезаем до 200 символов (лимит БД)
        if username and len(username) > 200:
            logger.warning(
                f"[RAW-TRANSCRIPT] Meeting {meeting_id}: username truncated from {len(username)} to 200 chars"
            )
            username = username[:200]
        
        # Проверяем на дубликаты через кэш
        message_id = decoded_data.get("message_id")
        text = decoded_data["text"]
        version = decoded_data.get("version", 1)
        
        is_duplicate = message_cache_service.is_duplicate(
            meeting_id=meeting_id,
            message_id=message_id,
            device_id=device_id,
            text=text,
            version=version
        )
        
        saved = False
        if not is_duplicate:
            # Сохраняем сегмент в БД
            try:
                timestamp = request.timestamp or datetime.now(timezone.utc)
                
                segment = TranscriptSegment(
                    session_id=session_id,
                    google_meet_user_id=device_id,
                    speaker_username=username,
                    timestamp=timestamp,
                    text=text,
                    version=version,
                    message_id=str(message_id) if message_id else None
                )
                
                db.add(segment)
                try:
                    await db.commit()
                    await db.refresh(segment)
                    
                    saved = True
                    
                    # Сохраняем в кэш только если успешно сохранили
                    message_cache_service.cache_message(
                        meeting_id=meeting_id,
                        message_id=message_id,
                        device_id=device_id,
                        text=text,
                        version=version
                    )
                except IntegrityError as e:
                    # Если дубликат - это нормально, просто пропускаем
                    await db.rollback()
                    logger.debug(
                        f"[RAW-TRANSCRIPT] Meeting {meeting_id}: Duplicate segment detected, skipping. "
                        f"device_id={device_id}, message_id={message_id}, text={text[:50]}..."
                    )
                    saved = False
                
                if saved:
                    logger.info(
                        f"Saved transcript segment for meeting {meeting_id}: "
                        f"device_id={device_id}, username={username}, message_id={message_id}"
                    )
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to save segment for meeting {meeting_id}: {str(e)}", exc_info=True)
                return RawTranscriptResponse(
                    success=True,
                    decoded=DecodedData(
                        device_id=device_id,
                        message_id=message_id,
                        text=text,
                        version=version,
                        lang_id=decoded_data.get("lang_id"),
                        username=username
                    ),
                    saved=False,
                    error=f"Failed to save segment: {str(e)}"
                )
        else:
            logger.debug(f"Skipped duplicate message for meeting {meeting_id}: message_id={message_id}")
        
        # Формируем ответ
        return RawTranscriptResponse(
            success=True,
            decoded=DecodedData(
                device_id=device_id,
                message_id=message_id,
                text=text,
                version=version,
                lang_id=decoded_data.get("lang_id"),
                username=username
            ),
            saved=saved
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing raw transcript for meeting {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process raw transcript: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(meeting_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    meeting_service = MeetingService(db)
    session_id = f"{meeting_id}-{user.id}"
    
    # Get the meeting and verify ownership
    result = await db.execute(
        select(Meeting).where(
            Meeting.unique_session_id == session_id,
            Meeting.user_id == user.id,
        ).limit(1)
    )
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    
    # Get segments for this meeting
    segments = await meeting_service.get_latest_segments_for_session(session_id=session_id)
    
    # Get speakers for this specific meeting
    speakers_result = await db.execute(
        select(TranscriptSegment.speaker_username)
        .where(TranscriptSegment.session_id == session_id)
        .distinct()
    )
    meeting_speakers = speakers_result.scalars().all()
    
    # Convert segments to schemas - ADD from_attributes=True
    segments_out = [TranscriptSegmentOut.model_validate(segment, from_attributes=True) for segment in segments]
    
    # Create meeting dict with all data
    meeting_dict = {
        "unique_session_id": meeting.unique_session_id,
        "meeting_id": meeting.meeting_id,
        "user_id": meeting.user_id,
        "title": meeting.title,
        "created_at": meeting.created_at,
        "speakers": meeting_speakers,
        "segments": segments_out
    }
    
    return MeetingOut(**meeting_dict)



@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete the user's meeting by meeting_id (scoped to the authenticated user).
    This removes the meeting row and cascades to related data (segments, chat, participants).
    """
    session_id = f"{meeting_id}-{user.id}"

    # Find the meeting owned by the user
    result = await db.execute(
        select(Meeting).where(
            Meeting.unique_session_id == session_id,
            Meeting.user_id == user.id,
        ).limit(1)
    )
    meeting = result.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Delete and commit (FKs are set to CASCADE)
    await db.delete(meeting)
    await db.commit()

    return Response(status_code=204)


# @router.get("/test/segments/{session_id}", response_model=list[TranscriptSegmentOut])
# def get_test_segments(session_id: str, db: Session = Depends(get_db)):
#     """
#     Тестовый эндпоинт для получения обработанных сегментов без авторизации.
#     """
#     meeting_service = MeetingService(db)
#     segments = meeting_service.get_latest_segments_for_session(session_id=session_id)
#     if not segments:
#         raise HTTPException(status_code=404, detail="No segments found for this session ID")
#     return segments
