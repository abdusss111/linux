"""
Tests for meeting API endpoints.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
from httpx import AsyncClient

from tests.factories import MeetingFactory, TranscriptSegmentFactory, UserFactory


class TestMeetingList:
    """Test meeting list endpoint with pagination."""
    
    @pytest.mark.asyncio
    async def test_get_meetings_empty(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting meetings when user has no meetings."""
        response = await async_test_client.get("/api/meetings", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meetings"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert data["has_more"] == False
    
    @pytest.mark.asyncio
    async def test_get_meetings_with_data(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test getting meetings with existing data."""
        # Create test meetings
        meetings = []
        for i in range(3):
            meeting = MeetingFactory.create(
                user_id=test_user.id,
                meeting_id=f"meeting_{i}",
                title=f"Meeting {i}"
            )
            async_db_session.add(meeting)
            meetings.append(meeting)
        
        await async_db_session.commit()
        
        response = await async_test_client.get("/api/meetings", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["meetings"]) == 3
        assert data["total"] == 3
        assert data["has_more"] == False
        
        # Verify meeting data
        for i, meeting_data in enumerate(data["meetings"]):
            assert meeting_data["meeting_id"] == f"meeting_{i}"
            assert meeting_data["title"] == f"Meeting {i}"
            assert meeting_data["user_id"] == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_meetings_pagination(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test meeting pagination."""
        # Create 5 test meetings
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
        response = await async_test_client.get(
            "/api/meetings?limit=2&offset=0", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["meetings"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert data["has_more"] == True
        
        # Test second page
        response = await async_test_client.get(
            "/api/meetings?limit=2&offset=2", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["meetings"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 2
        assert data["has_more"] == True
        
        # Test last page
        response = await async_test_client.get(
            "/api/meetings?limit=2&offset=4", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["meetings"]) == 1
        assert data["total"] == 5
        assert data["has_more"] == False
    
    @pytest.mark.asyncio
    async def test_get_meetings_limit_enforcement(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test that limit parameter is properly enforced."""
        # Test limit too high (should be capped at 100)
        response = await async_test_client.get(
            "/api/meetings?limit=200", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 100
        
        # Test limit too low (should be at least 1)
        response = await async_test_client.get(
            "/api/meetings?limit=0", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["limit"] == 1
        
        # Test negative offset (should be at least 0)
        response = await async_test_client.get(
            "/api/meetings?offset=-5", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_get_meetings_unauthorized(
        self, 
        async_test_client: AsyncClient
    ):
        """Test getting meetings without authentication."""
        response = await async_test_client.get("/api/meetings")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeetingCreation:
    """Test meeting creation and retrieval."""
    
    @pytest.mark.asyncio
    async def test_create_meeting_success(
        self, 
        async_test_client: AsyncClient, 
        test_user,
        auth_headers: dict
    ):
        """Test successful meeting creation."""
        meeting_data = {
            "id": "new_meeting_123",
            "title": "New Test Meeting"
        }
        
        response = await async_test_client.post(
            "/api/meetings", 
            json=meeting_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_id"] == "new_meeting_123"
        assert data["title"] == "New Test Meeting"
        assert data["user_id"] == test_user.id
        assert "unique_session_id" in data
        assert "created_at" in data
        assert data["unique_session_id"] == f"new_meeting_123-{test_user.id}"
    
    @pytest.mark.asyncio
    async def test_create_meeting_duplicate_id(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test creating meeting with same ID returns existing meeting."""
        # Create initial meeting
        meeting_data = {
            "id": "duplicate_meeting",
            "title": "Original Meeting"
        }
        
        response1 = await async_test_client.post(
            "/api/meetings", 
            json=meeting_data, 
            headers=auth_headers
        )
        
        assert response1.status_code == status.HTTP_200_OK
        original_data = response1.json()
        
        # Try to create meeting with same ID
        meeting_data["title"] = "Updated Title"
        response2 = await async_test_client.post(
            "/api/meetings", 
            json=meeting_data, 
            headers=auth_headers
        )
        
        assert response2.status_code == status.HTTP_200_OK
        duplicate_data = response2.json()
        
        # Should return the same meeting (24h window logic)
        assert duplicate_data["unique_session_id"] == original_data["unique_session_id"]
        assert duplicate_data["meeting_id"] == original_data["meeting_id"]
    
    @pytest.mark.asyncio
    async def test_create_meeting_validation_error(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test meeting creation with invalid data."""
        # Missing required fields
        response = await async_test_client.post(
            "/api/meetings", 
            json={}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing title
        response = await async_test_client.post(
            "/api/meetings", 
            json={"id": "test_meeting"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing id
        response = await async_test_client.post(
            "/api/meetings", 
            json={"title": "Test Meeting"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestMeetingRetrieval:
    """Test individual meeting retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_meeting_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        test_meeting,
        auth_headers: dict
    ):
        """Test successful meeting retrieval."""
        # Add some segments to the meeting
        segments = []
        for i in range(3):
            segment = TranscriptSegmentFactory.create(
                session_id=test_meeting.unique_session_id,
                speaker_username=f"Speaker {i}",
                text=f"Segment {i}"
            )
            async_db_session.add(segment)
            segments.append(segment)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_id"] == test_meeting.meeting_id
        assert data["title"] == test_meeting.title
        assert data["user_id"] == test_user.id
        assert len(data["segments"]) == 3
        assert len(data["speakers"]) == 3
        
        # Verify segments data
        for i, segment in enumerate(data["segments"]):
            assert segment["text"] == f"Segment {i}"
            assert segment["speaker_username"] == f"Speaker {i}"
    
    @pytest.mark.asyncio
    async def test_get_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting non-existent meeting."""
        response = await async_test_client.get(
            "/api/meetings/nonexistent_meeting", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_meeting_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user_2,
        test_meeting
    ):
        """Test getting meeting from different user."""
        # Create auth headers for different user
        from tests.conftest import auth_headers_user_2
        headers = auth_headers_user_2
        
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]


class TestMeetingDeletion:
    """Test meeting deletion."""
    
    @pytest.mark.asyncio
    async def test_delete_meeting_success(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test successful meeting deletion."""
        response = await async_test_client.delete(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify meeting is deleted
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test deleting non-existent meeting."""
        response = await async_test_client.delete(
            "/api/meetings/nonexistent_meeting", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_meeting_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test deleting meeting from different user."""
        # Create auth headers for different user
        from tests.conftest import auth_headers_user_2
        headers = auth_headers_user_2
        
        response = await async_test_client.delete(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]


class TestMeetingInfo:
    """Test meeting info endpoint (24-hour window logic)."""
    
    @pytest.mark.asyncio
    async def test_get_meeting_info_recent(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test getting info for recent meeting (< 24 hours)."""
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}/info", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_id"] == test_meeting.meeting_id
        assert data["title"] == test_meeting.title
    
    @pytest.mark.asyncio
    async def test_get_meeting_info_old(
        self, 
        async_test_client: AsyncClient, 
        test_meeting_old,
        auth_headers: dict
    ):
        """Test getting info for old meeting (>= 24 hours)."""
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting_old.meeting_id}/info", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_meeting_info_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting info for non-existent meeting."""
        response = await async_test_client.get(
            "/api/meetings/nonexistent_meeting/info", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]


class TestSegmentManagement:
    """Test transcript segment management."""
    
    @pytest.mark.asyncio
    async def test_add_segment_success(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test successful segment addition."""
        segment_data = {
            "google_meet_user_id": "user_123",
            "username": "Test Speaker",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "Test segment text",
            "ver": 1,
            "mess_id": "msg_123"
        }
        
        response = await async_test_client.post(
            f"/api/meetings/{test_meeting.meeting_id}/segments", 
            json=segment_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["text"] == "Test segment text"
        assert data["speaker_username"] == "Test Speaker"
        assert data["session_id"] == test_meeting.unique_session_id
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_add_segment_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test adding segment to non-existent meeting."""
        segment_data = {
            "google_meet_user_id": "user_123",
            "username": "Test Speaker",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "Test segment text",
            "ver": 1,
            "mess_id": "msg_123"
        }
        
        response = await async_test_client.post(
            "/api/meetings/nonexistent_meeting/segments", 
            json=segment_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_add_segment_validation_error(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test adding segment with invalid data."""
        # Missing required fields
        response = await async_test_client.post(
            f"/api/meetings/{test_meeting.meeting_id}/segments", 
            json={}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_add_segment_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test adding segment to meeting from different user."""
        # Create auth headers for different user
        from tests.conftest import auth_headers_user_2
        headers = auth_headers_user_2
        
        segment_data = {
            "google_meet_user_id": "user_123",
            "username": "Test Speaker",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": "Test segment text",
            "ver": 1,
            "mess_id": "msg_123"
        }
        
        response = await async_test_client.post(
            f"/api/meetings/{test_meeting.meeting_id}/segments", 
            json=segment_data, 
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found" in response.json()["detail"]


class TestMeetingWithSegments:
    """Test meeting retrieval with segments and speaker aggregation."""
    
    @pytest.mark.asyncio
    async def test_meeting_with_multiple_speakers(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test meeting retrieval with multiple speakers."""
        # Create segments with different speakers
        speakers = ["Alice", "Bob", "Charlie", "Alice", "Bob"]
        segments = []
        
        for i, speaker in enumerate(speakers):
            segment = TranscriptSegmentFactory.create(
                session_id=test_meeting.unique_session_id,
                speaker_username=speaker,
                text=f"Message from {speaker}",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i*10)
            )
            async_db_session.add(segment)
            segments.append(segment)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have unique speakers
        assert len(data["speakers"]) == 3
        assert "Alice" in data["speakers"]
        assert "Bob" in data["speakers"]
        assert "Charlie" in data["speakers"]
        
        # Should have all segments
        assert len(data["segments"]) == 5
    
    @pytest.mark.asyncio
    async def test_meeting_with_no_segments(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test meeting retrieval with no segments."""
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["segments"] == []
        assert data["speakers"] == []
    
    @pytest.mark.asyncio
    async def test_meeting_segments_ordered_by_timestamp(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test that segments are ordered by timestamp."""
        # Create segments with specific timestamps
        base_time = datetime.now(timezone.utc)
        timestamps = [
            base_time + timedelta(seconds=30),
            base_time + timedelta(seconds=10),
            base_time + timedelta(seconds=20)
        ]
        
        segments = []
        for i, timestamp in enumerate(timestamps):
            segment = TranscriptSegmentFactory.create(
                session_id=test_meeting.unique_session_id,
                speaker_username=f"Speaker {i}",
                text=f"Segment {i}",
                timestamp=timestamp
            )
            async_db_session.add(segment)
            segments.append(segment)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            f"/api/meetings/{test_meeting.meeting_id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Segments should be ordered by timestamp
        assert len(data["segments"]) == 3
        assert data["segments"][0]["text"] == "Segment 1"  # 10 seconds
        assert data["segments"][1]["text"] == "Segment 2"  # 20 seconds
        assert data["segments"][2]["text"] == "Segment 0"  # 30 seconds
