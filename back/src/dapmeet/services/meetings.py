from sqlalchemy.orm import noload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, desc, delete
from dapmeet.models.meeting import Meeting
from dapmeet.models.segment import TranscriptSegment
from dapmeet.models.user import User
from datetime import datetime, timedelta, timezone
from dapmeet.schemas.meetings import MeetingCreate, MeetingOutList
from dapmeet.models.chat_message import ChatMessage


class MeetingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_meeting(self, meeting_data: MeetingCreate, user: User) -> Meeting:
        """
        Получает или создаёт встречу по уникальному ID сессии.
        Правила:
        - Если встреча (последняя) существует и с момента её создания прошло >= 24 часов —
            создаём новую с unique_session_id = "<base_session_id>-<YYYY-MM-DD>" (дата без времени).
        - Если прошло < 24 часов — продолжаем писать в существующую.
        - Если встречи нет — создаём новую (без суффикса).
        """
        base_session_id = f"{meeting_data.id}-{user.id}"
        now_utc = datetime.now(timezone.utc)

        # Ищем последнюю встречу по этому base_session_id (включая старые с суффиксом даты)
        result = await self.db.execute(
            select(Meeting)
            .where(Meeting.unique_session_id.like(f"{base_session_id}%"))
            .order_by(desc(Meeting.created_at))
            .limit(1)
        )
        last_meeting = result.scalar_one_or_none()

        if last_meeting:
            age = now_utc - last_meeting.created_at
            if age < timedelta(hours=24):
                # Меньше 24 часов — используем существующую встречу
                return last_meeting
            else:
                # Больше/равно 24 часов — создаём новую с суффиксом даты (без времени)
                suffix = now_utc.date().isoformat()  # YYYY-MM-DD
                new_unique_session_id = f"{base_session_id}-{suffix}"

                new_meeting = Meeting(
                    unique_session_id=new_unique_session_id,
                    meeting_id=meeting_data.id,
                    user_id=user.id,
                    title=meeting_data.title,
                    subscription_plan=None,  # Will be set by API endpoint
                )
                self.db.add(new_meeting)
                await self.db.commit()
                await self.db.refresh(new_meeting)
                return new_meeting

        # Встреч не было — создаём первую (без суффикса)
        new_meeting = Meeting(
            unique_session_id=base_session_id,
            meeting_id=meeting_data.id,
            user_id=user.id,
            title=meeting_data.title,
            subscription_plan=None,  # Will be set by API endpoint
        )
        self.db.add(new_meeting)
        await self.db.commit()
        await self.db.refresh(new_meeting)
        return new_meeting
    async def get_meeting_by_session_id(self, session_id: str, user_id: str) -> Meeting | None:
        """Получает одну встречу по ID сессии без связанных сегментов."""
        u_session_id = f"{session_id}-{user_id}"
        result = await self.db.execute(
            select(Meeting)
            .options(noload(Meeting.segments))
            .where(Meeting.unique_session_id == u_session_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_segments_for_session(self, session_id: str) -> list[TranscriptSegment]:
        """
        Получает и обрабатывает сегменты транскрипции для указанной сессии,
        используя SQL-запрос для фильтрации и сортировки.
        Optimized version with better indexing support.
        """
        # Если в этой сессии НЕТ ни одной строки с message_id NOT NULL – значит это "атомарные" сегменты
        # (как наши модельные Model/whisper сегменты). В этом случае не делаем дедупликацию, просто возвращаем все.
        msg_check = await self.db.execute(
            select(func.count())
            .where(TranscriptSegment.session_id == session_id, TranscriptSegment.message_id.isnot(None))
        )
        has_message_ids = (msg_check.scalar() or 0) > 0

        if not has_message_ids:
            # Простой путь – все сегменты по времени и версии.
            plain_q = (
                select(TranscriptSegment)
                .where(TranscriptSegment.session_id == session_id)
                .order_by(TranscriptSegment.timestamp, TranscriptSegment.version)
            )
            res = await self.db.execute(plain_q)
            return list(res.scalars().all())

        # Старый путь дедупликации (для потоковых/обновляемых сообщений с версиями/ message_id)
        partition_key = TranscriptSegment.google_meet_user_id + '-' + TranscriptSegment.message_id
        cte = (
            select(
                TranscriptSegment,
                func.row_number()
                .over(
                    partition_by=partition_key,
                    order_by=[TranscriptSegment.message_id, TranscriptSegment.version.desc()],
                )
                .label("row_num"),
                func.min(TranscriptSegment.created_at)
                .over(partition_by=partition_key)
                .label("min_timestamp"),
            )
            .where(TranscriptSegment.session_id == session_id)
            .cte("ranked_segments")
        )

        segment_columns = [c for c in cte.c if c.name not in ("row_num", "min_timestamp")]

        query = (
            select(*segment_columns)
            .where(cte.c.row_num == 1)
            .order_by(cte.c.min_timestamp, cte.c.timestamp, cte.c.version)
        )
        exec_result = await self.db.execute(query)
        rows = exec_result.mappings().all()
        return [TranscriptSegment(**row) for row in rows]

    # In MeetingService
    async def get_meetings_with_speakers(self, user_id: int, session_id: str = None, limit: int = 50, offset: int = 0) -> list[MeetingOutList]:
        """
        Get meetings with speakers - optimized version with pagination
        
        Args:
            user_id: User ID to filter meetings
            session_id: Optional session ID to get specific meeting only
            limit: Maximum number of meetings to return (default 50)
            offset: Number of meetings to skip (default 0)
        
        Returns:
            List of MeetingOutList objects
        """
        # First, get meetings with pagination (much faster)
        meetings_stmt = (
            select(Meeting)
            .where(Meeting.user_id == user_id)
            .order_by(Meeting.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        # Add session filter if specified
        if session_id:
            meetings_stmt = meetings_stmt.where(Meeting.unique_session_id == session_id)
        
        exec_result = await self.db.execute(meetings_stmt)
        meetings = exec_result.scalars().all()
        
        if not meetings:
            return []
        
        # Get unique session IDs for the meetings
        session_ids = [meeting.unique_session_id for meeting in meetings]
        
        # Get speakers for these specific meetings using a more efficient query
        speakers_stmt = (
            select(
                TranscriptSegment.session_id,
                func.array_agg(func.distinct(TranscriptSegment.speaker_username)).label('speakers')
            )
            .where(TranscriptSegment.session_id.in_(session_ids))
            .group_by(TranscriptSegment.session_id)
        )
        
        speakers_result = await self.db.execute(speakers_stmt)
        speakers_data = {row.session_id: [s for s in (row.speakers or []) if s is not None] 
                        for row in speakers_result.all()}
        
        # Get latest AI chat message per session
        ranked_msgs = (
            select(
                ChatMessage.session_id,
                ChatMessage.content,
                func.row_number()
                .over(
                    partition_by=ChatMessage.session_id,
                    order_by=ChatMessage.created_at.desc()
                )
                .label("rn"),
            )
            .where(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.sender == 'ai'
            )
            .cte("ranked_msgs")
        )
        latest_ai_stmt = select(ranked_msgs.c.session_id, ranked_msgs.c.content).where(ranked_msgs.c.rn == 1)
        latest_ai_result = await self.db.execute(latest_ai_stmt)
        last_message_by_session = {row.session_id: row.content for row in latest_ai_result.all()}
        
        # Build the result
        return [
            MeetingOutList(
                unique_session_id=meeting.unique_session_id,
                meeting_id=meeting.meeting_id,
                user_id=meeting.user_id,
                title=meeting.title,
                created_at=meeting.created_at,
                speakers=speakers_data.get(meeting.unique_session_id, []),
                last_message=last_message_by_session.get(meeting.unique_session_id),
            )
            for meeting in meetings
        ]
    
    async def get_meetings_count(self, user_id: int) -> int:
        """
        Get total count of meetings for a user (for pagination metadata)
        """
        count_stmt = (
            select(func.count(Meeting.unique_session_id))
            .where(Meeting.user_id == user_id)
        )
        result = await self.db.execute(count_stmt)
        return result.scalar() or 0
        
