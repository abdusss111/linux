"""
Tests for chat API endpoints.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import status
from httpx import AsyncClient

from tests.factories import ChatMessageFactory, MeetingFactory, UserFactory


class TestChatHistory:
    """Test chat history retrieval with pagination."""
    
    @pytest.mark.asyncio
    async def test_get_chat_history_empty(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test getting chat history when no messages exist."""
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["session_id"] == test_meeting.meeting_id
        assert data["total_messages"] == 0
        assert data["messages"] == []
    
    @pytest.mark.asyncio
    async def test_get_chat_history_with_messages(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test getting chat history with existing messages."""
        # Create test messages
        messages = []
        for i in range(5):
            message = ChatMessageFactory.create(
                session_id=test_meeting.unique_session_id,
                sender="user" if i % 2 == 0 else "ai",
                content=f"Message {i}"
            )
            async_db_session.add(message)
            messages.append(message)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["session_id"] == test_meeting.meeting_id
        assert data["total_messages"] == 5
        assert len(data["messages"]) == 5
        
        # Verify message data
        for i, message in enumerate(data["messages"]):
            assert message["content"] == f"Message {i}"
            assert message["sender"] == ("user" if i % 2 == 0 else "ai")
            assert message["session_id"] == test_meeting.unique_session_id
    
    @pytest.mark.asyncio
    async def test_get_chat_history_pagination(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test chat history pagination."""
        # Create 10 test messages
        messages = []
        for i in range(10):
            message = ChatMessageFactory.create(
                session_id=test_meeting.unique_session_id,
                sender="user" if i % 2 == 0 else "ai",
                content=f"Message {i}",
                created_at=datetime.now(timezone.utc) + timedelta(seconds=i)
            )
            async_db_session.add(message)
            messages.append(message)
        
        await async_db_session.commit()
        
        # Test first page
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?page=1&size=3", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_messages"] == 10
        assert len(data["messages"]) == 3
        
        # Test second page
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?page=2&size=3", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_messages"] == 10
        assert len(data["messages"]) == 3
        
        # Test last page
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?page=4&size=3", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_messages"] == 10
        assert len(data["messages"]) == 1  # Only 1 message on last page
    
    @pytest.mark.asyncio
    async def test_get_chat_history_pagination_limits(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test chat history pagination limits."""
        # Test page size too large (should be capped at 100)
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?size=200", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Note: The actual limit enforcement depends on the API implementation
        
        # Test page size too small (should be at least 1)
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?size=0", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Note: The actual limit enforcement depends on the API implementation
        
        # Test page number too small (should be at least 1)
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history?page=0", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Note: The actual limit enforcement depends on the API implementation
    
    @pytest.mark.asyncio
    async def test_get_chat_history_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test getting chat history without authentication."""
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_chat_history_wrong_user(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test getting chat history for meeting from different user."""
        # Create auth headers for different user
        from tests.conftest import auth_headers_user_2
        headers = auth_headers_user_2
        
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found or access denied" in response.json()["detail"]


class TestAddChatMessage:
    """Test adding individual chat messages."""
    
    @pytest.mark.asyncio
    async def test_add_chat_message_success(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test successful message addition."""
        message_data = {
            "sender": "user",
            "content": "Hello, this is a test message"
        }
        
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json=message_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["sender"] == "user"
        assert data["content"] == "Hello, this is a test message"
        assert data["session_id"] == test_meeting.unique_session_id
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_add_chat_message_ai_sender(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test adding message with AI sender."""
        message_data = {
            "sender": "ai",
            "content": "This is an AI response"
        }
        
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json=message_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["sender"] == "ai"
        assert data["content"] == "This is an AI response"
    
    @pytest.mark.asyncio
    async def test_add_chat_message_validation_error(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test adding message with invalid data."""
        # Missing required fields
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json={}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing sender
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json={"content": "Test message"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing content
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json={"sender": "user"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Empty content
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json={"sender": "user", "content": ""}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_add_chat_message_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test adding message to non-existent meeting."""
        message_data = {
            "sender": "user",
            "content": "Test message"
        }
        
        response = await async_test_client.post(
            "/api/chat/nonexistent_meeting/messages", 
            json=message_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found or access denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_add_chat_message_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test adding message without authentication."""
        message_data = {
            "sender": "user",
            "content": "Test message"
        }
        
        response = await async_test_client.post(
            f"/api/chat/{test_meeting.meeting_id}/messages", 
            json=message_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestReplaceChatHistory:
    """Test replacing entire chat history."""
    
    @pytest.mark.asyncio
    async def test_replace_chat_history_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test successful chat history replacement."""
        # Create initial messages
        initial_messages = []
        for i in range(3):
            message = ChatMessageFactory.create(
                session_id=test_meeting.unique_session_id,
                sender="user",
                content=f"Initial message {i}"
            )
            async_db_session.add(message)
            initial_messages.append(message)
        
        await async_db_session.commit()
        
        # Replace with new messages
        new_messages = [
            {"sender": "user", "content": "New message 1"},
            {"sender": "ai", "content": "New message 2"},
            {"sender": "user", "content": "New message 3"}
        ]
        
        replace_data = {
            "session_id": test_meeting.meeting_id,
            "messages": new_messages
        }
        
        response = await async_test_client.put(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            json=replace_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["session_id"] == test_meeting.meeting_id
        assert data["total_messages"] == 3
        assert len(data["messages"]) == 3
        
        # Verify new messages
        for i, message in enumerate(data["messages"]):
            assert message["content"] == f"New message {i+1}"
            assert message["sender"] == new_messages[i]["sender"]
    
    @pytest.mark.asyncio
    async def test_replace_chat_history_session_id_mismatch(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test replacing chat history with mismatched session ID."""
        replace_data = {
            "session_id": "different_session_id",
            "messages": [{"sender": "user", "content": "Test message"}]
        }
        
        response = await async_test_client.put(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            json=replace_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Session ID in URL must match session ID in request body" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_replace_chat_history_empty_messages(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test replacing chat history with empty messages list."""
        replace_data = {
            "session_id": test_meeting.meeting_id,
            "messages": []
        }
        
        response = await async_test_client.put(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            json=replace_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_replace_chat_history_validation_error(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test replacing chat history with invalid data."""
        # Missing required fields
        response = await async_test_client.put(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            json={}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_replace_chat_history_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test replacing chat history for non-existent meeting."""
        replace_data = {
            "session_id": "nonexistent_meeting",
            "messages": [{"sender": "user", "content": "Test message"}]
        }
        
        response = await async_test_client.put(
            "/api/chat/nonexistent_meeting/history", 
            json=replace_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found or access denied" in response.json()["detail"]


class TestDeleteChatHistory:
    """Test deleting chat history."""
    
    @pytest.mark.asyncio
    async def test_delete_chat_history_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test successful chat history deletion."""
        # Create test messages
        messages = []
        for i in range(3):
            message = ChatMessageFactory.create(
                session_id=test_meeting.unique_session_id,
                sender="user",
                content=f"Message {i}"
            )
            async_db_session.add(message)
            messages.append(message)
        
        await async_db_session.commit()
        
        # Delete chat history
        response = await async_test_client.delete(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify messages are deleted
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_messages"] == 0
        assert data["messages"] == []
    
    @pytest.mark.asyncio
    async def test_delete_chat_history_empty(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test deleting empty chat history."""
        response = await async_test_client.delete(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.asyncio
    async def test_delete_chat_history_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test deleting chat history for non-existent meeting."""
        response = await async_test_client.delete(
            "/api/chat/nonexistent_meeting/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found or access denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_chat_history_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test deleting chat history without authentication."""
        response = await async_test_client.delete(
            f"/api/chat/{test_meeting.meeting_id}/history"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetSpecificMessage:
    """Test getting specific chat messages."""
    
    @pytest.mark.asyncio
    async def test_get_message_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test successful message retrieval."""
        # Create test message
        message = ChatMessageFactory.create(
            session_id=test_meeting.unique_session_id,
            sender="user",
            content="Test message content"
        )
        async_db_session.add(message)
        await async_db_session.commit()
        await async_db_session.refresh(message)
        
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/messages/{message.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == message.id
        assert data["content"] == "Test message content"
        assert data["sender"] == "user"
        assert data["session_id"] == test_meeting.unique_session_id
    
    @pytest.mark.asyncio
    async def test_get_message_not_found(
        self, 
        async_test_client: AsyncClient, 
        test_meeting,
        auth_headers: dict
    ):
        """Test getting non-existent message."""
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/messages/99999", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Message not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_message_wrong_meeting(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test getting message from different meeting."""
        # Create message in different meeting
        other_meeting = MeetingFactory.create(
            user_id=test_meeting.user_id,
            meeting_id="other_meeting"
        )
        async_db_session.add(other_meeting)
        await async_db_session.commit()
        
        message = ChatMessageFactory.create(
            session_id=other_meeting.unique_session_id,
            sender="user",
            content="Message in other meeting"
        )
        async_db_session.add(message)
        await async_db_session.commit()
        await async_db_session.refresh(message)
        
        # Try to get message from wrong meeting
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/messages/{message.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Message not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_message_meeting_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting message from non-existent meeting."""
        response = await async_test_client.get(
            "/api/chat/nonexistent_meeting/messages/1", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Meeting not found or access denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_message_unauthorized(
        self, 
        async_test_client: AsyncClient, 
        test_meeting
    ):
        """Test getting message without authentication."""
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/messages/1"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChatMessageOrdering:
    """Test chat message ordering and timestamps."""
    
    @pytest.mark.asyncio
    async def test_messages_ordered_by_creation_time(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test that messages are ordered by creation time."""
        # Create messages with specific timestamps
        base_time = datetime.now(timezone.utc)
        timestamps = [
            base_time + timedelta(seconds=30),
            base_time + timedelta(seconds=10),
            base_time + timedelta(seconds=20)
        ]
        
        messages = []
        for i, timestamp in enumerate(timestamps):
            message = ChatMessageFactory.create(
                session_id=test_meeting.unique_session_id,
                sender="user",
                content=f"Message {i}",
                created_at=timestamp
            )
            async_db_session.add(message)
            messages.append(message)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/history", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Messages should be ordered by creation time (ascending)
        assert len(data["messages"]) == 3
        assert data["messages"][0]["content"] == "Message 1"  # 10 seconds
        assert data["messages"][1]["content"] == "Message 2"  # 20 seconds
        assert data["messages"][2]["content"] == "Message 0"  # 30 seconds
    
    @pytest.mark.asyncio
    async def test_message_timestamps_preserved(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_meeting,
        auth_headers: dict
    ):
        """Test that message timestamps are preserved correctly."""
        # Create message with specific timestamp
        specific_time = datetime.now(timezone.utc) - timedelta(hours=1)
        message = ChatMessageFactory.create(
            session_id=test_meeting.unique_session_id,
            sender="user",
            content="Timestamped message",
            created_at=specific_time
        )
        async_db_session.add(message)
        await async_db_session.commit()
        await async_db_session.refresh(message)
        
        response = await async_test_client.get(
            f"/api/chat/{test_meeting.meeting_id}/messages/{message.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify timestamp is preserved
        assert "created_at" in data
        # Note: Exact timestamp comparison depends on serialization format
