"""
Tests for Whisper transcription API endpoints.
"""
import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from io import BytesIO

from tests.factories import MeetingFactory, UserFactory


class TestWhisperTranscription:
    """Test Whisper transcription functionality."""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_segments_success(
        self, 
        async_test_client: AsyncClient, 
        test_user,
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test successful transcription with segments."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "This is a test transcription",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "This is a test"
                },
                {
                    "start": 2.5,
                    "end": 4.0,
                    "text": "transcription"
                }
            ]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "This is a test transcription"
        assert len(data["segments"]) == 2
        assert data["segments"][0]["text"] == "This is a test"
        assert data["segments"][0]["start"] == 0.0
        assert data["segments"][0]["end"] == 2.5
        assert data["segments"][1]["text"] == "transcription"
        assert data["segments"][1]["start"] == 2.5
        assert data["segments"][1]["end"] == 4.0
        assert data["model_used"] == "whisper-1"  # Should switch to whisper-1 for segments
        assert data["model_switched"] == True
    
    @pytest.mark.asyncio
    async def test_transcribe_without_segments_success(
        self, 
        async_test_client: AsyncClient, 
        test_user,
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test successful transcription without segments."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "This is a simple transcription"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=false&model=gpt-4o-mini-transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "This is a simple transcription"
        assert "segments" not in data
        assert data["model_used"] == "gpt-4o-mini-transcribe"
        assert data["model_switched"] == False
    
    @pytest.mark.asyncio
    async def test_transcribe_with_meeting_storage(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with meeting storage."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Meeting transcription with segments",
            "segments": [
                {
                    "start": 0.0,
                    "end": 3.0,
                    "text": "Meeting transcription"
                },
                {
                    "start": 3.0,
                    "end": 5.0,
                    "text": "with segments"
                }
            ]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true&meeting_id=test_meeting&meeting_title=Test Meeting&store=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "Meeting transcription with segments"
        assert len(data["segments"]) == 2
        assert data["meeting_session_id"] is not None
        assert data["segments_saved"] == 2
        
        # Verify meeting was created
        from dapmeet.models.meeting import Meeting
        from sqlalchemy import select
        
        result = await async_db_session.execute(
            select(Meeting).where(Meeting.meeting_id == "test_meeting")
        )
        meeting = result.scalar_one_or_none()
        assert meeting is not None
        assert meeting.title == "Test Meeting"
        assert meeting.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_file(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test transcription with empty file."""
        # Create empty file
        files = {"file": ("empty.wav", BytesIO(b""), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Empty file" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_transcribe_file_too_large(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test transcription with file exceeding size limit."""
        # Create large file (26MB)
        large_content = b"x" * (26 * 1024 * 1024)
        files = {"file": ("large.wav", BytesIO(large_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "File exceeds 25MB limit" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_transcribe_missing_file(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test transcription without file."""
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_transcribe_unauthorized(
        self, 
        async_test_client: AsyncClient
    ):
        """Test transcription without authentication."""
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            files=files
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_transcribe_openai_error(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with OpenAI API error."""
        # Mock OpenAI error
        mock_openai_whisper.side_effect = Exception("OpenAI API error")
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Transcription failed" in response.json()["detail"]
        assert "OpenAI API error" in response.json()["detail"]


class TestModelSwitching:
    """Test model switching logic."""
    
    @pytest.mark.asyncio
    async def test_model_switches_to_whisper_for_segments(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test that model switches to whisper-1 when segments are requested."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test transcription"}]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true&model=gpt-4o-mini-transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["model_requested"] == "gpt-4o-mini-transcribe"
        assert data["model_used"] == "whisper-1"
        assert data["model_switched"] == True
    
    @pytest.mark.asyncio
    async def test_model_no_switch_when_whisper_requested(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test that model doesn't switch when whisper-1 is already requested."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Test transcription"}]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true&model=whisper-1",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["model_requested"] == "whisper-1"
        assert data["model_used"] == "whisper-1"
        assert data["model_switched"] == False
    
    @pytest.mark.asyncio
    async def test_model_no_switch_without_segments(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test that model doesn't switch when segments are not requested."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=false&model=gpt-4o-mini-transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["model_requested"] == "gpt-4o-mini-transcribe"
        assert data["model_used"] == "gpt-4o-mini-transcribe"
        assert data["model_switched"] == False


class TestTranscriptionParameters:
    """Test transcription parameters and options."""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_prompt(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with custom prompt."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription with prompt"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?prompt=This is a technical meeting",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify prompt was passed to OpenAI
        mock_openai_whisper.assert_called_once()
        call_args = mock_openai_whisper.call_args
        assert call_args[1]["prompt"] == "This is a technical meeting"
    
    @pytest.mark.asyncio
    async def test_transcribe_with_response_format(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with custom response format."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?response_format=text&with_segments=false",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify response format was passed to OpenAI
        mock_openai_whisper.assert_called_once()
        call_args = mock_openai_whisper.call_args
        assert call_args[1]["response_format"] == "text"
    
    @pytest.mark.asyncio
    async def test_transcribe_with_filename(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with custom filename."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Test transcription"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("custom_name.mp3", BytesIO(audio_content), "audio/mp3")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify filename was passed to OpenAI
        mock_openai_whisper.assert_called_once()
        call_args = mock_openai_whisper.call_args
        assert call_args[1]["filename"] == "custom_name.mp3"


class TestMeetingIntegration:
    """Test meeting integration features."""
    
    @pytest.mark.asyncio
    async def test_transcribe_creates_new_meeting(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test that transcription creates a new meeting when specified."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "New meeting transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "New meeting transcription"}]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?meeting_id=new_meeting&meeting_title=New Meeting&store=true&with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_session_id"] is not None
        assert data["segments_saved"] == 1
        
        # Verify meeting was created
        from dapmeet.models.meeting import Meeting
        from sqlalchemy import select
        
        result = await async_db_session.execute(
            select(Meeting).where(Meeting.meeting_id == "new_meeting")
        )
        meeting = result.scalar_one_or_none()
        assert meeting is not None
        assert meeting.title == "New Meeting"
        assert meeting.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_transcribe_uses_existing_meeting(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test that transcription uses existing meeting when available."""
        # Create existing meeting
        existing_meeting = MeetingFactory.create(
            user_id=test_user.id,
            meeting_id="existing_meeting",
            title="Existing Meeting"
        )
        async_db_session.add(existing_meeting)
        await async_db_session.commit()
        
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Additional transcription",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Additional transcription"}]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?meeting_id=existing_meeting&store=true&with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_session_id"] == existing_meeting.unique_session_id
        assert data["segments_saved"] == 1
    
    @pytest.mark.asyncio
    async def test_transcribe_without_meeting_storage(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription without meeting storage."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Transcription without storage",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Transcription without storage"}]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?meeting_id=test_meeting&store=false&with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["meeting_session_id"] is None
        assert data["segments_saved"] == 0
    
    @pytest.mark.asyncio
    async def test_transcribe_meeting_without_segments(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with meeting but without segments."""
        # Mock OpenAI response
        mock_openai_whisper.return_value = {
            "text": "Simple transcription"
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?meeting_id=test_meeting&store=true&with_segments=false",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "Simple transcription"
        assert "segments" not in data
        assert data["meeting_session_id"] is None
        assert data["segments_saved"] == 0


class TestSegmentProcessing:
    """Test segment processing and validation."""
    
    @pytest.mark.asyncio
    async def test_segment_processing_with_empty_segments(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with empty segments."""
        # Mock OpenAI response with empty segments
        mock_openai_whisper.return_value = {
            "text": "Test transcription",
            "segments": []
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "Test transcription"
        assert data["segments"] == []
    
    @pytest.mark.asyncio
    async def test_segment_processing_with_invalid_segments(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with invalid segment data."""
        # Mock OpenAI response with invalid segments
        mock_openai_whisper.return_value = {
            "text": "Test transcription",
            "segments": [
                {"start": "invalid", "end": 2.0, "text": "Valid segment"},
                {"start": 2.0, "end": "invalid", "text": "Invalid end"},
                {"start": 3.0, "end": 4.0, "text": ""},  # Empty text
                {"start": 4.0, "end": 5.0, "text": "Valid segment 2"}
            ]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "Test transcription"
        # Should only include valid segments
        assert len(data["segments"]) == 1
        assert data["segments"][0]["text"] == "Valid segment 2"
    
    @pytest.mark.asyncio
    async def test_segment_processing_with_missing_fields(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict,
        mock_openai_whisper
    ):
        """Test transcription with segments missing required fields."""
        # Mock OpenAI response with incomplete segments
        mock_openai_whisper.return_value = {
            "text": "Test transcription",
            "segments": [
                {"start": 0.0, "text": "Missing end"},  # Missing end
                {"end": 2.0, "text": "Missing start"},  # Missing start
                {"start": 2.0, "end": 3.0},  # Missing text
                {"start": 3.0, "end": 4.0, "text": "Complete segment"}
            ]
        }
        
        # Create test audio file
        audio_content = b"fake audio content"
        files = {"file": ("test_audio.wav", BytesIO(audio_content), "audio/wav")}
        
        response = await async_test_client.post(
            "/api/whisper/transcribe?with_segments=true",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["text"] == "Test transcription"
        # Should only include complete segments
        assert len(data["segments"]) == 1
        assert data["segments"][0]["text"] == "Complete segment"
        assert data["segments"][0]["start"] == 3.0
        assert data["segments"][0]["end"] == 4.0
