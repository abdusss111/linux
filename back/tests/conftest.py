"""
Pytest configuration and fixtures for DapMeet tests.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dapmeet.cmd.main import app
from dapmeet.db.db import Base
from dapmeet.core.deps import get_async_db, get_db
from dapmeet.models.user import User
from dapmeet.models.meeting import Meeting
from dapmeet.models.chat_message import ChatMessage
from dapmeet.models.prompt import Prompt
from dapmeet.models.segment import TranscriptSegment
from dapmeet.services.google_auth_service import generate_jwt


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
SQLALCHEMY_DATABASE_URL_ASYNC = "sqlite+aiosqlite:///./test_async.db"

# Create test engines
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL_ASYNC,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestingAsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestingAsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Drop tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
    
    # Drop tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(async_db_session: AsyncSession) -> TestClient:
    """Create a test client with database dependency override."""
    
    async def override_get_async_db():
        yield async_db_session
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def async_test_client(async_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database dependency override."""
    
    async def override_get_async_db():
        yield async_db_session
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(async_db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id="test_user_123",
        email="test@example.com",
        name="Test User",
        auth_provider="google"
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(async_db_session: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        id="test_user_456",
        email="test2@example.com",
        name="Test User 2",
        auth_provider="google"
    )
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for test user."""
    jwt_token = generate_jwt({
        "id": test_user.id,
        "email": test_user.email,
        "name": test_user.name
    })
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture
def auth_headers_user_2(test_user_2: User) -> dict:
    """Generate authentication headers for second test user."""
    jwt_token = generate_jwt({
        "id": test_user_2.id,
        "email": test_user_2.email,
        "name": test_user_2.name
    })
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest_asyncio.fixture
async def test_meeting(async_db_session: AsyncSession, test_user: User) -> Meeting:
    """Create a test meeting."""
    meeting = Meeting(
        unique_session_id=f"meeting_123-{test_user.id}",
        meeting_id="meeting_123",
        user_id=test_user.id,
        title="Test Meeting"
    )
    async_db_session.add(meeting)
    await async_db_session.commit()
    await async_db_session.refresh(meeting)
    return meeting


@pytest_asyncio.fixture
async def test_meeting_old(async_db_session: AsyncSession, test_user: User) -> Meeting:
    """Create an old test meeting (older than 24 hours)."""
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    meeting = Meeting(
        unique_session_id=f"old_meeting-{test_user.id}",
        meeting_id="old_meeting",
        user_id=test_user.id,
        title="Old Meeting",
        created_at=old_time
    )
    async_db_session.add(meeting)
    await async_db_session.commit()
    await async_db_session.refresh(meeting)
    return meeting


@pytest_asyncio.fixture
async def test_segments(async_db_session: AsyncSession, test_meeting: Meeting) -> list[TranscriptSegment]:
    """Create test transcript segments."""
    segments = []
    for i in range(3):
        segment = TranscriptSegment(
            session_id=test_meeting.unique_session_id,
            google_meet_user_id=f"user_{i}",
            speaker_username=f"Speaker {i}",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=i*10),
            text=f"Test segment {i}",
            version=1
        )
        async_db_session.add(segment)
        segments.append(segment)
    
    await async_db_session.commit()
    for segment in segments:
        await async_db_session.refresh(segment)
    return segments


@pytest_asyncio.fixture
async def test_chat_messages(async_db_session: AsyncSession, test_meeting: Meeting) -> list[ChatMessage]:
    """Create test chat messages."""
    messages = []
    for i in range(3):
        message = ChatMessage(
            session_id=test_meeting.unique_session_id,
            sender="user" if i % 2 == 0 else "ai",
            content=f"Test message {i}"
        )
        async_db_session.add(message)
        messages.append(message)
    
    await async_db_session.commit()
    for message in messages:
        await async_db_session.refresh(message)
    return messages


@pytest_asyncio.fixture
async def test_prompt(async_db_session: AsyncSession, test_user: User) -> Prompt:
    """Create a test user prompt."""
    prompt = Prompt(
        name="test_prompt",
        content="Test prompt content",
        prompt_type="user",
        user_id=test_user.id,
        is_active=True
    )
    async_db_session.add(prompt)
    await async_db_session.commit()
    await async_db_session.refresh(prompt)
    return prompt


@pytest_asyncio.fixture
async def test_admin_prompt(async_db_session: AsyncSession) -> Prompt:
    """Create a test admin prompt."""
    prompt = Prompt(
        name="admin_prompt",
        content="Admin prompt content",
        prompt_type="admin",
        user_id=None,
        is_active=True
    )
    async_db_session.add(prompt)
    await async_db_session.commit()
    await async_db_session.refresh(prompt)
    return prompt


# Mock fixtures for external services
@pytest.fixture
def mock_google_auth():
    """Mock Google authentication services."""
    with patch('dapmeet.services.google_auth_service.exchange_code_for_token') as mock_exchange, \
         patch('dapmeet.services.google_auth_service.get_google_user_info') as mock_user_info, \
         patch('dapmeet.services.google_auth_service.validate_google_access_token') as mock_validate:
        
        mock_exchange.return_value = "mock_access_token"
        mock_user_info.return_value = {
            "id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_validate.return_value = {
            "audience": "test_client_id",
            "expires_in": 3600
        }
        
        yield {
            "exchange": mock_exchange,
            "user_info": mock_user_info,
            "validate": mock_validate
        }


@pytest.fixture
def mock_openai_whisper():
    """Mock OpenAI Whisper API."""
    with patch('dapmeet.services.whisper.WhisperService.transcribe_file') as mock_transcribe:
        mock_transcribe.return_value = {
            "text": "Test transcription",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Test segment"
                }
            ]
        }
        yield mock_transcribe


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    with patch('dapmeet.services.email_service.email_service.send_welcome_email') as mock_send:
        mock_send.return_value = AsyncMock()
        yield mock_send


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    
    with patch('dapmeet.core.deps.get_http_client', return_value=mock_client):
        yield mock_client


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user_data(user_id: str = "test_user_123", email: str = "test@example.com") -> dict:
        return {
            "id": user_id,
            "email": email,
            "name": "Test User",
            "auth_provider": "google"
        }
    
    @staticmethod
    def create_meeting_data(meeting_id: str = "meeting_123", user_id: str = "test_user_123") -> dict:
        return {
            "id": meeting_id,
            "title": "Test Meeting"
        }
    
    @staticmethod
    def create_segment_data(session_id: str, speaker: str = "Speaker 1") -> dict:
        return {
            "google_meet_user_id": "user_1",
            "username": speaker,
            "timestamp": datetime.now(timezone.utc),
            "text": "Test segment text",
            "ver": 1,
            "mess_id": "msg_123"
        }
    
    @staticmethod
    def create_chat_message_data(sender: str = "user", content: str = "Test message") -> dict:
        return {
            "sender": sender,
            "content": content
        }
    
    @staticmethod
    def create_prompt_data(name: str = "test_prompt", content: str = "Test content") -> dict:
        return {
            "name": name,
            "content": content,
            "prompt_type": "user",
            "is_active": True
        }


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Provide test data factory."""
    return TestDataFactory()
