"""
Tests for MeetingService business logic.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from dapmeet.services.meetings import MeetingService
from dapmeet.schemas.meetings import MeetingCreate
from tests.factories import MeetingFactory, TranscriptSegmentFactory, UserFactory, ChatMessageFactory


class TestMeetingService:
    """Test MeetingService business logic."""
    
    @pytest.fixture
    def meeting_service(self, async_db_session: AsyncSession) -> MeetingService:
        """Create MeetingService instance."""
        return MeetingService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_get_or_create_meeting_new_meeting(
        self, 
        meeting_service: MeetingService, 
        test_user
    ):
        """Test creating a new meeting."""
        meeting_data = MeetingCreate(id="new_meeting", title="New Meeting")
        
        meeting = await meeting_service.get_or_create_meeting(meeting_data, test_user)
        
        assert meeting.meeting_id == "new_meeting"
        assert meeting.title == "New Meeting"
        assert meeting.user_id == test_user.id
        assert meeting.unique_session_id == f"new_meeting-{test_user.id}"
        assert meeting.created_at is not None
    
    @pytest.mark.asyncio
    async def test_get_or_create_meeting_existing_recent(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting existing recent meeting (< 24 hours)."""
        # Create existing meeting
        existing_meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="existing_meeting",
            title="Existing Meeting",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        async_db_session.add(existing_meeting)
        await async_db_session.commit()
        
        meeting_data = MeetingCreate(id="existing_meeting", title="Updated Title")
        
        meeting = await meeting_service.get_or_create_meeting(meeting_data, test_user)
        
        # Should return existing meeting
        assert meeting.id == existing_meeting.id
        assert meeting.meeting_id == "existing_meeting"
        assert meeting.title == "Existing Meeting"  # Title should not change
        assert meeting.unique_session_id == existing_meeting.unique_session_id
    
    @pytest.mark.asyncio
    async def test_get_or_create_meeting_existing_old(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test creating new meeting when existing is old (>= 24 hours)."""
        # Create old meeting
        old_meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="old_meeting",
            title="Old Meeting",
            created_at=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        async_db_session.add(old_meeting)
        await async_db_session.commit()
        
        meeting_data = MeetingCreate(id="old_meeting", title="New Meeting")
        
        meeting = await meeting_service.get_or_create_meeting(meeting_data, test_user)
        
        # Should create new meeting with date suffix
        assert meeting.meeting_id == "old_meeting"
        assert meeting.title == "New Meeting"
        assert meeting.user_id == test_user.id
        assert meeting.unique_session_id != old_meeting.unique_session_id
        assert meeting.unique_session_id.startswith(f"old_meeting-{test_user.id}-")
        assert meeting.created_at > old_meeting.created_at
    
    @pytest.mark.asyncio
    async def test_get_meeting_by_session_id_success(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting meeting by session ID."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        result = await meeting_service.get_meeting_by_session_id("test_meeting", test_user.id)
        
        assert result is not None
        assert result.meeting_id == "test_meeting"
        assert result.user_id == test_user.id
        assert result.unique_session_id == f"test_meeting-{test_user.id}"
    
    @pytest.mark.asyncio
    async def test_get_meeting_by_session_id_not_found(
        self, 
        meeting_service: MeetingService, 
        test_user
    ):
        """Test getting non-existent meeting by session ID."""
        result = await meeting_service.get_meeting_by_session_id("nonexistent_meeting", test_user.id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_meeting_by_session_id_wrong_user(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user,
        test_user_2
    ):
        """Test getting meeting by session ID for different user."""
        # Create meeting for test_user
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        # Try to get with different user
        result = await meeting_service.get_meeting_by_session_id("test_meeting", test_user_2.id)
        
        assert result is None


class TestSegmentProcessing:
    """Test transcript segment processing logic."""
    
    @pytest.fixture
    def meeting_service(self, async_db_session: AsyncSession) -> MeetingService:
        """Create MeetingService instance."""
        return MeetingService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_get_latest_segments_simple_segments(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting segments without message IDs (simple segments)."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        # Create simple segments (no message_id)
        segments = []
        for i in range(3):
            segment = TranscriptSegmentFactory.create(
                session_id=meeting.unique_session_id,
                speaker_username=f"Speaker {i}",
                text=f"Segment {i}",
                message_id=None
            )
            async_db_session.add(segment)
            segments.append(segment)
        
        await async_db_session.commit()
        
        result = await meeting_service.get_latest_segments_for_session(meeting.unique_session_id)
        
        assert len(result) == 3
        for i, segment in enumerate(result):
            assert segment.text == f"Segment {i}"
            assert segment.speaker_username == f"Speaker {i}"
    
    @pytest.mark.asyncio
    async def test_get_latest_segments_with_message_ids(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting segments with message IDs (deduplication)."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        # Create segments with message IDs and versions
        segments = []
        for i in range(2):  # Two messages
            for v in range(3):  # Three versions each
                segment = TranscriptSegmentFactory.create(
                    session_id=meeting.unique_session_id,
                    speaker_username=f"Speaker {i}",
                    text=f"Message {i} Version {v}",
                    message_id=f"msg_{i}",
                    version=v + 1
                )
                async_db_session.add(segment)
                segments.append(segment)
        
        await async_db_session.commit()
        
        result = await meeting_service.get_latest_segments_for_session(meeting.unique_session_id)
        
        # Should return only latest version of each message
        assert len(result) == 2
        assert result[0].text == "Message 0 Version 2"  # Latest version
        assert result[1].text == "Message 1 Version 2"  # Latest version
    
    @pytest.mark.asyncio
    async def test_get_latest_segments_empty(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting segments when none exist."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        result = await meeting_service.get_latest_segments_for_session(meeting.unique_session_id)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_latest_segments_ordered_by_timestamp(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test that segments are ordered by timestamp."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="test_meeting",
            title="Test Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        # Create segments with specific timestamps
        base_time = datetime.now(timezone.utc)
        timestamps = [
            base_time + timedelta(seconds=30),
            base_time + timedelta(seconds=10),
            base_time + timedelta(seconds=20)
        ]
        
        for i, timestamp in enumerate(timestamps):
            segment = TranscriptSegmentFactory.create(
                session_id=meeting.unique_session_id,
                speaker_username=f"Speaker {i}",
                text=f"Segment {i}",
                timestamp=timestamp,
                message_id=None
            )
            async_db_session.add(segment)
        
        await async_db_session.commit()
        
        result = await meeting_service.get_latest_segments_for_session(meeting.unique_session_id)
        
        # Should be ordered by timestamp
        assert len(result) == 3
        assert result[0].text == "Segment 1"  # 10 seconds
        assert result[1].text == "Segment 2"  # 20 seconds
        assert result[2].text == "Segment 0"  # 30 seconds


class TestMeetingListWithSpeakers:
    """Test meeting list with speaker aggregation."""
    
    @pytest.fixture
    def meeting_service(self, async_db_session: AsyncSession) -> MeetingService:
        """Create MeetingService instance."""
        return MeetingService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_get_meetings_with_speakers_empty(
        self, 
        meeting_service: MeetingService, 
        test_user
    ):
        """Test getting meetings when user has no meetings."""
        result = await meeting_service.get_meetings_with_speakers(test_user.id)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_meetings_with_speakers_success(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting meetings with speaker aggregation."""
        # Create meetings
        meetings = []
        for i in range(2):
            meeting = MeetingFactory.create(
                user_id=test_user.id,
                meeting_id=f"meeting_{i}",
                title=f"Meeting {i}"
            )
            async_db_session.add(meeting)
            meetings.append(meeting)
        
        await async_db_session.commit()
        
        # Create segments with speakers
        speakers_data = [
            ["Alice", "Bob", "Alice"],  # Meeting 0 speakers
            ["Charlie", "David"]        # Meeting 1 speakers
        ]
        
        for meeting_idx, meeting in enumerate(meetings):
            for speaker in speakers_data[meeting_idx]:
                segment = TranscriptSegmentFactory.create(
                    session_id=meeting.unique_session_id,
                    speaker_username=speaker,
                    text=f"Message from {speaker}",
                    message_id=None
                )
                async_db_session.add(segment)
        
        await async_db_session.commit()
        
        result = await meeting_service.get_meetings_with_speakers(test_user.id)
        
        assert len(result) == 2
        
        # Check first meeting
        meeting_0 = result[0]
        assert meeting_0.meeting_id == "meeting_0"
        assert meeting_0.title == "Meeting 0"
        assert set(meeting_0.speakers) == {"Alice", "Bob"}
        
        # Check second meeting
        meeting_1 = result[1]
        assert meeting_1.meeting_id == "meeting_1"
        assert meeting_1.title == "Meeting 1"
        assert set(meeting_1.speakers) == {"Charlie", "David"}
    
    @pytest.mark.asyncio
    async def test_get_meetings_with_speakers_pagination(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test meeting pagination."""
        # Create 5 meetings
        meetings = []
        for i in range(5):
            meeting = MeetingFactory.create(
                user_id=test_user.id,
                meeting_id=f"meeting_{i}",
                title=f"Meeting {i}"
            )
            async_db_session.add(meeting)
            meetings.append(meeting)
        
        await async_db_session.commit()
        
        # Test first page
        result = await meeting_service.get_meetings_with_speakers(
            test_user.id, limit=2, offset=0
        )
        
        assert len(result) == 2
        assert result[0].meeting_id == "meeting_4"  # Most recent first
        assert result[1].meeting_id == "meeting_3"
        
        # Test second page
        result = await meeting_service.get_meetings_with_speakers(
            test_user.id, limit=2, offset=2
        )
        
        assert len(result) == 2
        assert result[0].meeting_id == "meeting_2"
        assert result[1].meeting_id == "meeting_1"
    
    @pytest.mark.asyncio
    async def test_get_meetings_with_speakers_with_chat_messages(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting meetings with last AI chat message."""
        # Create meeting
        meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="chat_meeting",
            title="Chat Meeting"
        )
        async_db_session.add(meeting)
        await async_db_session.commit()
        
        # Create chat messages
        messages = [
            ChatMessageFactory.create(
                session_id=meeting.unique_session_id,
                sender="user",
                content="User message 1"
            ),
            ChatMessageFactory.create(
                session_id=meeting.unique_session_id,
                sender="ai",
                content="AI response 1"
            ),
            ChatMessageFactory.create(
                session_id=meeting.unique_session_id,
                sender="user",
                content="User message 2"
            ),
            ChatMessageFactory.create(
                session_id=meeting.unique_session_id,
                sender="ai",
                content="AI response 2"
            )
        ]
        
        for message in messages:
            async_db_session.add(message)
        
        await async_db_session.commit()
        
        result = await meeting_service.get_meetings_with_speakers(test_user.id)
        
        assert len(result) == 1
        meeting_result = result[0]
        assert meeting_result.meeting_id == "chat_meeting"
        assert meeting_result.last_message == "AI response 2"  # Latest AI message
    
    @pytest.mark.asyncio
    async def test_get_meetings_count(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting meeting count."""
        # Create 3 meetings
        for i in range(3):
            meeting = MeetingFactory.create(
                user_id=test_user.id,
                meeting_id=f"meeting_{i}",
                title=f"Meeting {i}"
            )
            async_db_session.add(meeting)
        
        await async_db_session.commit()
        
        count = await meeting_service.get_meetings_count(test_user.id)
        
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_meetings_count_empty(
        self, 
        meeting_service: MeetingService, 
        test_user
    ):
        """Test getting meeting count when user has no meetings."""
        count = await meeting_service.get_meetings_count(test_user.id)
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_meetings_count_different_users(
        self, 
        meeting_service: MeetingService, 
        async_db_session: AsyncSession,
        test_user,
        test_user_2
    ):
        """Test getting meeting count for different users."""
        # Create meetings for test_user
        for i in range(2):
            meeting = MeetingFactory.create(
                user_id=test_user.id,
                meeting_id=f"user1_meeting_{i}",
                title=f"User 1 Meeting {i}"
            )
            async_db_session.add(meeting)
        
        # Create meetings for test_user_2
        for i in range(3):
            meeting = MeetingFactory.create(
                user_id=test_user_2.id,
                meeting_id=f"user2_meeting_{i}",
                title=f"User 2 Meeting {i}"
            )
            async_db_session.add(meeting)
        
        await async_db_session.commit()
        
        # Test counts
        count_user1 = await meeting_service.get_meetings_count(test_user.id)
        count_user2 = await meeting_service.get_meetings_count(test_user_2.id)
        
        assert count_user1 == 2
        assert count_user2 == 3
