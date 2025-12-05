from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends, Form
import logging
from datetime import timedelta, datetime, timezone
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dapmeet.core.deps import get_async_db
from dapmeet.services.meetings import MeetingService
from dapmeet.models.segment import TranscriptSegment
from dapmeet.services.whisper import WhisperService
from dapmeet.services.auth import get_current_user
from dapmeet.models.user import User
from dapmeet.schemas.meetings import MeetingOut

router = APIRouter()
log = logging.getLogger("transcribe_api")

class AudioSource(str, Enum):
    MIC = "MIC"
    TAB = "TAB"

def get_whisper_service() -> WhisperService:  # keeping name for DI
    return WhisperService()


###############################
# Single transcription endpoint
###############################

@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    response_format: str = Query("json", description="Desired high-level format (json / text) when segments not needed"),
    prompt: str | None = Query(None, description="Optional prompt to guide transcription"),
    with_segments: bool = Query(True, description="Return segments with timestamps (switches model to whisper-1 if needed)"),
    model: str = Query("gpt-4o-mini-transcribe", description="Base model: gpt-4o-mini-transcribe or whisper-1 for timestamps"),
    meeting_id: str | None = Query(None, description="If provided – store segments into meeting (auto create/get)."),
    meeting_title: str | None = Query(None, description="Optional meeting title when creating new meeting."),
    store: bool = Query(True, description="Store segments if meeting_id provided."),
    svc: WhisperService = Depends(get_whisper_service),
    user: User = Depends(get_current_user),  # auth check
    db: AsyncSession = Depends(get_async_db),
):
    """Transcribe audio.

    Logic:
      - If with_segments=true we need real timestamps -> use whisper-1 (verbose_json). If caller passed a non-whisper model, we auto-switch and report this in response.
      - If with_segments=false we use requested model & response_format as-is.
    """
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > 25:
        raise HTTPException(413, "File exceeds 25MB limit")
    chosen_model = model
    internal_format = response_format
    model_switched = False
    if with_segments:
        # Need a model that supports verbose_json (whisper-1). gpt-4o-mini-transcribe doesn't.
        if model != "whisper-1":
            chosen_model = "whisper-1"
            model_switched = True
        internal_format = "verbose_json"
    try:
        raw_result = svc.transcribe_file(
            data,
            file.filename or "audio",
            model=chosen_model,
            response_format=internal_format,
            prompt=prompt,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Transcribe failed filename=%s", file.filename)
        raise HTTPException(502, f"Transcription failed. Type={e.__class__.__name__} Message={e}")

    if not with_segments:
        # Attach model info for clarity
        if isinstance(raw_result, dict):
            raw_result.setdefault("model_used", chosen_model)
        return raw_result

    # Expect verbose_json structure with segments
    segments_raw = raw_result.get("segments") if isinstance(raw_result, dict) else None
    simplified = []
    if isinstance(segments_raw, list):
        for i, seg in enumerate(segments_raw):
            try:
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", start))
                text_seg = (seg.get("text") or "").strip()
                if text_seg:
                    simplified.append({
                        "index": i,
                        "start": start,
                        "end": end,
                        "text": text_seg,
                    })
            except Exception:  # noqa: BLE001
                continue

    meeting_session_id = None
    segments_saved = 0
    if meeting_id and store and simplified:
        # create or reuse meeting (24h window logic in MeetingService)
        meeting_service = MeetingService(db)
        meeting = await meeting_service.get_or_create_meeting(
            meeting_data=type("Tmp", (), {"id": meeting_id, "title": meeting_title or meeting_id})(),
            user=user,
        )
        meeting_session_id = meeting.unique_session_id
        base_ts = meeting.created_at
        for seg in simplified:
            start = seg.get("start", 0.0) or 0.0
            text_seg = seg.get("text") or ""
            if not text_seg:
                continue
            ts = base_ts + timedelta(seconds=float(start))
            rec = TranscriptSegment(
                session_id=meeting_session_id,
                google_meet_user_id="model",  # generic speaker id
                speaker_username="Model",
                timestamp=ts,
                text=text_seg,
            )
            db.add(rec)
            segments_saved += 1
        if segments_saved:
            await db.commit()

    return {
        "text": raw_result.get("text") if isinstance(raw_result, dict) else None,
        "segments": simplified,
        "model_requested": model,
        "model_used": chosen_model,
        "model_switched": model_switched,
        "meeting_session_id": meeting_session_id,
        "segments_saved": segments_saved,
        "raw": raw_result,
    }


###############################
# Chunked segments ingestion endpoint
###############################

@router.post("/segments/")
async def ingest_segment(
    audio: UploadFile = File(..., description="Audio blob; e.g., audio/webm;codecs=opus"),
    meetingId: str = Form(..., description="Meeting ID from Google Meet URL"),
    timestamp: datetime = Form(..., description="ISO start time of this chunk"),
    segmentId: str = Form(..., description="Unique segment ID for idempotency/versioning"),
    source: AudioSource = Form(..., description="Audio source: MIC or TAB"),
    svc: WhisperService = Depends(get_whisper_service),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Transcribe a 20-30s chunk and write a single `TranscriptSegment` for the meeting.

    - Accepts multipart form-data: audio, meetingId, timestamp, segmentId, source
    - Transcribes using OpenAI (default gpt-4o-mini-transcribe JSON)
    - Stores one segment at the provided timestamp, bound to the user's active meeting session
    - Uses `segmentId` in `message_id` for basic idempotency
    - If source=MIC: speaker is set to meeting owner's name
    - If source=TAB: speaker is set to "Другие"
    """
    # Read and validate file
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty file")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > 25:
        raise HTTPException(413, "File exceeds 25MB limit")

    # Transcribe chunk (JSON is sufficient since we provide the chunk timestamp)
    try:
        result = svc.transcribe_file(
            data,
            audio.filename or "audio",
            model="gpt-4o-mini-transcribe",
            response_format="json",
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Chunk transcription failed filename=%s", audio.filename)
        raise HTTPException(502, f"Transcription failed. Type={e.__class__.__name__} Message={e}")

    text = (result.get("text") or "").strip() if isinstance(result, dict) else ""
    if not text:
        # Nothing to store for this chunk
        return {
            "meeting_id": meetingId,
            "segment_id": segmentId,
            "stored": False,
            "reason": "empty_transcript",
        }

    # Ensure meeting exists (24h window) and get session id
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_or_create_meeting(
        meeting_data=type("Tmp", (), {"id": meetingId, "title": meetingId})(),
        user=user,
    )

    # Determine speaker based on source
    if source == AudioSource.MIC:
        # Use meeting owner's name, fallback to user email or "Speaker" if name is not available
        speaker_username = user.name or user.email or "Speaker"
    else:  # TAB
        speaker_username = "Другие"

    # Create transcript segment at provided timestamp
    record = TranscriptSegment(
        session_id=meeting.unique_session_id,
        google_meet_user_id="whisper-chunk",
        speaker_username=speaker_username,
        timestamp=timestamp,
        text=text,
        message_id=segmentId,
        version=1,
    )
    db.add(record)
    await db.commit()

    return {
        "meeting_session_id": meeting.unique_session_id,
        "meeting_id": meeting.meeting_id,
        "segment_id": segmentId,
        "stored": True,
        "chars": len(text),
        "model_used": "gpt-4o-mini-transcribe",
    }

###############################
# Transcribe v2 endpoint - Auto create meeting
###############################

@router.post("/transcribe-v2", response_model=MeetingOut)
async def transcribe_v2(
    file: UploadFile = File(...),
    title: str | None = File(None, description="Optional meeting title. If not provided, will use date-based title"),
    prompt: str | None = Query(None, description="Optional prompt to guide transcription"),
    svc: WhisperService = Depends(get_whisper_service),
    user: User = Depends(get_current_user),  # auth check
    db: AsyncSession = Depends(get_async_db),
):
    """
    Transcribe audio file and automatically create a meeting with the transcription.
    
    This endpoint:
    1. Accepts an audio file
    2. Transcribes it using OpenAI Whisper
    3. Automatically creates a new meeting with date-based title
    4. Stores all transcription segments in the meeting
    5. Returns the complete meeting with segments
    
    The meeting title can be provided via the 'title' parameter, or will default to date-based title (e.g., "Meeting - 2024-01-15").
    """
    # Read and validate file
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    size_mb = len(data) / (1024 * 1024)
    if size_mb > 100:
        raise HTTPException(413, "File exceeds 100MB limit")
    
    # Generate meeting ID and title
    now_utc = datetime.now(timezone.utc)
    meeting_id = f"transcribe-{now_utc.strftime('%Y%m%d-%H%M%S')}"
    
    # Use provided title or fallback to date-based title
    if title and title.strip():
        meeting_title = title.strip()
    else:
        meeting_title = f"Meeting - {now_utc.strftime('%Y-%m-%d')}"
    
    # Transcribe using whisper-1 for segments with timestamps
    try:
        raw_result = svc.transcribe_file(
            data,
            file.filename or "audio",
            model="whisper-1",  # Always use whisper-1 for timestamp support
            response_format="verbose_json",
            prompt=prompt,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Transcribe v2 failed filename=%s", file.filename)
        raise HTTPException(502, f"Transcription failed. Type={e.__class__.__name__} Message={e}")
    
    # Parse segments from verbose_json response
    segments_raw = raw_result.get("segments") if isinstance(raw_result, dict) else None
    if not isinstance(segments_raw, list):
        raise HTTPException(502, "Invalid transcription response - no segments found")
    
    # Create meeting
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_or_create_meeting(
        meeting_data=type("Tmp", (), {"id": meeting_id, "title": meeting_title})(),
        user=user,
    )
    
    # Store segments in the meeting
    base_ts = meeting.created_at
    segments_saved = 0
    
    for i, seg in enumerate(segments_raw):
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            text_seg = (seg.get("text") or "").strip()
            
            if not text_seg:
                continue
                
            # Calculate timestamp relative to meeting creation
            ts = base_ts + timedelta(seconds=float(start))
            
            # Create transcript segment
            transcript_segment = TranscriptSegment(
                session_id=meeting.unique_session_id,
                google_meet_user_id="transcribe-v2",  # identifier for this endpoint
                speaker_username="Speaker",  # generic speaker name
                timestamp=ts,
                text=text_seg,
            )
            db.add(transcript_segment)
            segments_saved += 1
            
        except Exception as e:  # noqa: BLE001
            log.warning("Failed to process segment %d: %s", i, e)
            continue
    
    # Commit all segments
    if segments_saved > 0:
        await db.commit()
        log.info("Saved %d segments for meeting %s", segments_saved, meeting.unique_session_id)
    else:
        log.warning("No segments were saved for meeting %s", meeting.unique_session_id)
    
    # Get the complete meeting with segments for response
    segments = await meeting_service.get_latest_segments_for_session(meeting.unique_session_id)
    
    # Get speakers for this meeting
    speakers_result = await db.execute(
        select(TranscriptSegment.speaker_username)
        .where(TranscriptSegment.session_id == meeting.unique_session_id)
        .distinct()
    )
    meeting_speakers = speakers_result.scalars().all()
    
    # Convert segments to schemas
    from dapmeet.schemas.segment import TranscriptSegmentOut
    segments_out = [TranscriptSegmentOut.model_validate(segment, from_attributes=True) for segment in segments]
    
    # Create meeting response
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

