"""
Test data factories for creating realistic test data.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from faker import Faker

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dapmeet.models.user import User
from dapmeet.models.meeting import Meeting
from dapmeet.models.chat_message import ChatMessage
from dapmeet.models.prompt import Prompt
from dapmeet.models.segment import TranscriptSegment

fake = Faker()


class UserFactory:
    """Factory for creating User test data."""
    
    @staticmethod
    def create(
        id: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        auth_provider: str = "google",
        phone_number: Optional[str] = None
    ) -> User:
        """Create a User instance with realistic test data."""
        return User(
            id=id or fake.uuid4(),
            email=email or fake.email(),
            name=name or fake.name(),
            auth_provider=auth_provider,
            phone_number=phone_number
        )
    
    @staticmethod
    def create_google_user() -> User:
        """Create a Google-authenticated user."""
        return UserFactory.create(auth_provider="google")
    
    @staticmethod
    def create_phone_user() -> User:
        """Create a phone-authenticated user."""
        return UserFactory.create(
            auth_provider="phone",
            email=None,
            phone_number=fake.phone_number()
        )
    
    @staticmethod
    def create_batch(count: int) -> List[User]:
        """Create multiple users."""
        return [UserFactory.create() for _ in range(count)]


class MeetingFactory:
    """Factory for creating Meeting test data."""
    
    @staticmethod
    def create(
        unique_session_id: Optional[str] = None,
        meeting_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> Meeting:
        """Create a Meeting instance with realistic test data."""
        if not unique_session_id and meeting_id and user_id:
            unique_session_id = f"{meeting_id}-{user_id}"
        
        return Meeting(
            unique_session_id=unique_session_id or f"{fake.word()}-{fake.uuid4()}",
            meeting_id=meeting_id or fake.word(),
            user_id=user_id or fake.uuid4(),
            title=title or fake.sentence(nb_words=3),
            created_at=created_at or datetime.now(timezone.utc)
        )
    
    @staticmethod
    def create_recent_meeting(user_id: str) -> Meeting:
        """Create a meeting from the last 24 hours."""
        recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
        return MeetingFactory.create(
            user_id=user_id,
            created_at=recent_time
        )
    
    @staticmethod
    def create_old_meeting(user_id: str) -> Meeting:
        """Create a meeting older than 24 hours."""
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        return MeetingFactory.create(
            user_id=user_id,
            created_at=old_time
        )
    
    @staticmethod
    def create_with_date_suffix(user_id: str, meeting_id: str) -> Meeting:
        """Create a meeting with date suffix (for 24h+ logic)."""
        today = datetime.now(timezone.utc).date().isoformat()
        unique_session_id = f"{meeting_id}-{user_id}-{today}"
        return MeetingFactory.create(
            unique_session_id=unique_session_id,
            meeting_id=meeting_id,
            user_id=user_id
        )


class ChatMessageFactory:
    """Factory for creating ChatMessage test data."""
    
    @staticmethod
    def create(
        session_id: Optional[str] = None,
        sender: Optional[str] = None,
        content: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> ChatMessage:
        """Create a ChatMessage instance with realistic test data."""
        return ChatMessage(
            session_id=session_id or f"{fake.word()}-{fake.uuid4()}",
            sender=sender or fake.random_element(elements=("user", "ai", "system")),
            content=content or fake.sentence(nb_words=10),
            created_at=created_at or datetime.now(timezone.utc)
        )
    
    @staticmethod
    def create_user_message(session_id: str) -> ChatMessage:
        """Create a user message."""
        return ChatMessageFactory.create(
            session_id=session_id,
            sender="user",
            content=fake.sentence(nb_words=8)
        )
    
    @staticmethod
    def create_ai_message(session_id: str) -> ChatMessage:
        """Create an AI message."""
        return ChatMessageFactory.create(
            session_id=session_id,
            sender="ai",
            content=fake.sentence(nb_words=12)
        )
    
    @staticmethod
    def create_conversation(session_id: str, message_count: int = 5) -> List[ChatMessage]:
        """Create a conversation with alternating user/AI messages."""
        messages = []
        for i in range(message_count):
            sender = "user" if i % 2 == 0 else "ai"
            message = ChatMessageFactory.create(
                session_id=session_id,
                sender=sender,
                created_at=datetime.now(timezone.utc) + timedelta(seconds=i*10)
            )
            messages.append(message)
        return messages


class PromptFactory:
    """Factory for creating Prompt test data."""
    
    @staticmethod
    def create(
        name: Optional[str] = None,
        content: Optional[str] = None,
        prompt_type: str = "user",
        user_id: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> Prompt:
        """Create a Prompt instance with realistic test data."""
        return Prompt(
            name=name or fake.word(),
            content=content or fake.text(max_nb_chars=500),
            prompt_type=prompt_type,
            user_id=user_id,
            is_active=is_active,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc)
        )
    
    @staticmethod
    def create_user_prompt(user_id: str) -> Prompt:
        """Create a user prompt."""
        return PromptFactory.create(
            prompt_type="user",
            user_id=user_id,
            name=f"user_prompt_{fake.word()}"
        )
    
    @staticmethod
    def create_admin_prompt() -> Prompt:
        """Create an admin prompt."""
        return PromptFactory.create(
            prompt_type="admin",
            user_id=None,
            name=f"admin_prompt_{fake.word()}"
        )
    
    @staticmethod
    def create_inactive_prompt(user_id: str) -> Prompt:
        """Create an inactive prompt."""
        return PromptFactory.create(
            prompt_type="user",
            user_id=user_id,
            is_active=False
        )


class TranscriptSegmentFactory:
    """Factory for creating TranscriptSegment test data."""
    
    @staticmethod
    def create(
        session_id: Optional[str] = None,
        google_meet_user_id: Optional[str] = None,
        speaker_username: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        text: Optional[str] = None,
        version: int = 1,
        message_id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> TranscriptSegment:
        """Create a TranscriptSegment instance with realistic test data."""
        return TranscriptSegment(
            session_id=session_id or f"{fake.word()}-{fake.uuid4()}",
            google_meet_user_id=google_meet_user_id or f"user_{fake.random_int(min=1, max=10)}",
            speaker_username=speaker_username or fake.name(),
            timestamp=timestamp or datetime.now(timezone.utc),
            text=text or fake.sentence(nb_words=8),
            version=version,
            message_id=message_id,
            created_at=created_at or datetime.now(timezone.utc)
        )
    
    @staticmethod
    def create_with_speaker(session_id: str, speaker: str) -> TranscriptSegment:
        """Create a segment with a specific speaker."""
        return TranscriptSegmentFactory.create(
            session_id=session_id,
            speaker_username=speaker,
            google_meet_user_id=f"user_{speaker.lower().replace(' ', '_')}"
        )
    
    @staticmethod
    def create_meeting_transcript(session_id: str, speaker_count: int = 3, segments_per_speaker: int = 5) -> List[TranscriptSegment]:
        """Create a realistic meeting transcript with multiple speakers."""
        segments = []
        speakers = [fake.name() for _ in range(speaker_count)]
        
        for speaker_idx, speaker in enumerate(speakers):
            for segment_idx in range(segments_per_speaker):
                segment = TranscriptSegmentFactory.create(
                    session_id=session_id,
                    speaker_username=speaker,
                    google_meet_user_id=f"user_{speaker_idx}",
                    timestamp=datetime.now(timezone.utc) + timedelta(seconds=(speaker_idx * segments_per_speaker + segment_idx) * 10),
                    text=fake.sentence(nb_words=fake.random_int(min=5, max=15))
                )
                segments.append(segment)
        
        return segments
    
    @staticmethod
    def create_updated_segment(session_id: str, message_id: str, version: int = 2) -> TranscriptSegment:
        """Create an updated segment (for testing versioning)."""
        return TranscriptSegmentFactory.create(
            session_id=session_id,
            message_id=message_id,
            version=version,
            text=fake.sentence(nb_words=10) + " (updated)"
        )


class TestDataBuilder:
    """Builder pattern for creating complex test scenarios."""
    
    def __init__(self):
        self.user = None
        self.meeting = None
        self.segments = []
        self.messages = []
        self.prompts = []
    
    def with_user(self, **kwargs) -> 'TestDataBuilder':
        """Add a user to the test scenario."""
        self.user = UserFactory.create(**kwargs)
        return self
    
    def with_meeting(self, **kwargs) -> 'TestDataBuilder':
        """Add a meeting to the test scenario."""
        if self.user and 'user_id' not in kwargs:
            kwargs['user_id'] = self.user.id
        self.meeting = MeetingFactory.create(**kwargs)
        return self
    
    def with_segments(self, count: int = 3, **kwargs) -> 'TestDataBuilder':
        """Add transcript segments to the test scenario."""
        if self.meeting and 'session_id' not in kwargs:
            kwargs['session_id'] = self.meeting.unique_session_id
        self.segments = [TranscriptSegmentFactory.create(**kwargs) for _ in range(count)]
        return self
    
    def with_messages(self, count: int = 5, **kwargs) -> 'TestDataBuilder':
        """Add chat messages to the test scenario."""
        if self.meeting and 'session_id' not in kwargs:
            kwargs['session_id'] = self.meeting.unique_session_id
        self.messages = ChatMessageFactory.create_conversation(
            session_id=kwargs.get('session_id', f"{fake.word()}-{fake.uuid4()}"),
            message_count=count
        )
        return self
    
    def with_prompts(self, count: int = 2, **kwargs) -> 'TestDataBuilder':
        """Add prompts to the test scenario."""
        if self.user and 'user_id' not in kwargs:
            kwargs['user_id'] = self.user.id
        self.prompts = [PromptFactory.create_user_prompt(self.user.id) for _ in range(count)]
        return self
    
    def build(self) -> dict:
        """Build the complete test scenario."""
        return {
            'user': self.user,
            'meeting': self.meeting,
            'segments': self.segments,
            'messages': self.messages,
            'prompts': self.prompts
        }


# Convenience functions for common test scenarios
def create_meeting_with_transcript(user_id: str, segment_count: int = 10) -> dict:
    """Create a complete meeting scenario with transcript."""
    builder = TestDataBuilder()
    return (builder
            .with_user(id=user_id)
            .with_meeting(user_id=user_id)
            .with_segments(count=segment_count)
            .build())


def create_meeting_with_chat(user_id: str, message_count: int = 8) -> dict:
    """Create a complete meeting scenario with chat history."""
    builder = TestDataBuilder()
    return (builder
            .with_user(id=user_id)
            .with_meeting(user_id=user_id)
            .with_messages(count=message_count)
            .build())


def create_user_with_prompts(user_id: str, prompt_count: int = 3) -> dict:
    """Create a user with multiple prompts."""
    builder = TestDataBuilder()
    return (builder
            .with_user(id=user_id)
            .with_prompts(count=prompt_count)
            .build())


def create_complete_scenario(user_id: str) -> dict:
    """Create a complete test scenario with all components."""
    builder = TestDataBuilder()
    return (builder
            .with_user(id=user_id)
            .with_meeting(user_id=user_id)
            .with_segments(count=5)
            .with_messages(count=6)
            .with_prompts(count=2)
            .build())
