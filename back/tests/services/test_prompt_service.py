"""
Tests for PromptService business logic.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dapmeet.services.prompts import PromptService
from dapmeet.schemas.prompt import PromptCreate, PromptUpdate, PromptSearchParams
from tests.factories import PromptFactory, UserFactory


class TestPromptService:
    """Test PromptService business logic."""
    
    @pytest.fixture
    def prompt_service(self, async_db_session: AsyncSession) -> PromptService:
        """Create PromptService instance."""
        return PromptService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_create_prompt_success(
        self, 
        prompt_service: PromptService, 
        test_user
    ):
        """Test successful prompt creation."""
        prompt_data = PromptCreate(
            name="test_prompt",
            content="Test prompt content",
            prompt_type="user",
            is_active=True
        )
        
        prompt = await prompt_service.create_prompt(prompt_data, test_user.id)
        
        assert prompt.name == "test_prompt"
        assert prompt.content == "Test prompt content"
        assert prompt.prompt_type == "user"
        assert prompt.user_id == test_user.id
        assert prompt.is_active == True
        assert prompt.id is not None
        assert prompt.created_at is not None
        assert prompt.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_prompt_duplicate_name(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test creating prompt with duplicate name."""
        # Create existing prompt
        existing_prompt = PromptFactory.create(
            name="duplicate_name",
            prompt_type="user",
            user_id=test_user.id
        )
        async_db_session.add(existing_prompt)
        await async_db_session.commit()
        
        prompt_data = PromptCreate(
            name="duplicate_name",
            content="Different content",
            prompt_type="user",
            is_active=True
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.create_prompt(prompt_data, test_user.id)
        
        assert exc_info.value.status_code == 400
        assert "Prompt with this name already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_prompt_admin(
        self, 
        prompt_service: PromptService
    ):
        """Test creating admin prompt."""
        prompt_data = PromptCreate(
            name="admin_prompt",
            content="Admin prompt content",
            prompt_type="admin",
            is_active=True
        )
        
        prompt = await prompt_service.create_prompt(prompt_data, user_id=None)
        
        assert prompt.name == "admin_prompt"
        assert prompt.content == "Admin prompt content"
        assert prompt.prompt_type == "admin"
        assert prompt.user_id is None
        assert prompt.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_prompt_by_id_success(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting prompt by ID."""
        # Create prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "test_prompt"
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        result = await prompt_service.get_prompt_by_id(prompt.id)
        
        assert result is not None
        assert result.id == prompt.id
        assert result.name == "test_prompt"
        assert result.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_prompt_by_id_not_found(
        self, 
        prompt_service: PromptService
    ):
        """Test getting non-existent prompt by ID."""
        result = await prompt_service.get_prompt_by_id(99999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_prompt_by_name_success(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting prompt by name."""
        # Create prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "named_prompt"
        prompt.is_active = True
        async_db_session.add(prompt)
        await async_db_session.commit()
        
        result = await prompt_service.get_prompt_by_name("named_prompt")
        
        assert result is not None
        assert result.name == "named_prompt"
        assert result.user_id == test_user.id
        assert result.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_prompt_by_name_not_found(
        self, 
        prompt_service: PromptService
    ):
        """Test getting non-existent prompt by name."""
        result = await prompt_service.get_prompt_by_name("nonexistent_prompt")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_prompt_by_name_inactive(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting inactive prompt by name."""
        # Create inactive prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "inactive_prompt"
        prompt.is_active = False
        async_db_session.add(prompt)
        await async_db_session.commit()
        
        result = await prompt_service.get_prompt_by_name("inactive_prompt")
        
        assert result is None  # Should not return inactive prompts


class TestPromptUpdate:
    """Test prompt update functionality."""
    
    @pytest.fixture
    def prompt_service(self, async_db_session: AsyncSession) -> PromptService:
        """Create PromptService instance."""
        return PromptService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_update_prompt_success(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test successful prompt update."""
        # Create prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "original_name"
        prompt.content = "Original content"
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        update_data = PromptUpdate(
            name="updated_name",
            content="Updated content",
            is_active=False
        )
        
        updated_prompt = await prompt_service.update_prompt(prompt.id, update_data, test_user.id)
        
        assert updated_prompt.id == prompt.id
        assert updated_prompt.name == "updated_name"
        assert updated_prompt.content == "Updated content"
        assert updated_prompt.is_active == False
        assert updated_prompt.updated_at > prompt.updated_at
    
    @pytest.mark.asyncio
    async def test_update_prompt_partial(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test partial prompt update."""
        # Create prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "original_name"
        prompt.content = "Original content"
        prompt.is_active = True
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        update_data = PromptUpdate(content="Only content updated")
        
        updated_prompt = await prompt_service.update_prompt(prompt.id, update_data, test_user.id)
        
        assert updated_prompt.id == prompt.id
        assert updated_prompt.name == "original_name"  # Should remain unchanged
        assert updated_prompt.content == "Only content updated"
        assert updated_prompt.is_active == True  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_update_prompt_not_found(
        self, 
        prompt_service: PromptService, 
        test_user
    ):
        """Test updating non-existent prompt."""
        update_data = PromptUpdate(content="Updated content")
        
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.update_prompt(99999, update_data, test_user.id)
        
        assert exc_info.value.status_code == 404
        assert "Prompt not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_prompt_wrong_owner(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user,
        test_user_2
    ):
        """Test updating prompt from different user."""
        # Create prompt for test_user
        prompt = PromptFactory.create_user_prompt(test_user.id)
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        update_data = PromptUpdate(content="Updated content")
        
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.update_prompt(prompt.id, update_data, test_user_2.id)
        
        assert exc_info.value.status_code == 403
        assert "You can only update your own prompts" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_prompt_duplicate_name(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test updating prompt with duplicate name."""
        # Create two prompts
        prompt1 = PromptFactory.create_user_prompt(test_user.id)
        prompt1.name = "prompt_1"
        async_db_session.add(prompt1)
        
        prompt2 = PromptFactory.create_user_prompt(test_user.id)
        prompt2.name = "prompt_2"
        async_db_session.add(prompt2)
        
        await async_db_session.commit()
        await async_db_session.refresh(prompt1)
        await async_db_session.refresh(prompt2)
        
        update_data = PromptUpdate(name="prompt_1")
        
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.update_prompt(prompt2.id, update_data, test_user.id)
        
        assert exc_info.value.status_code == 400
        assert "Prompt with this name already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_update_prompt_admin_can_update_any(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test that admin can update any prompt."""
        # Create user prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        prompt.name = "user_prompt"
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        update_data = PromptUpdate(content="Admin updated content")
        
        # Admin (no user_id) can update any prompt
        updated_prompt = await prompt_service.update_prompt(prompt.id, update_data, user_id=None)
        
        assert updated_prompt.content == "Admin updated content"


class TestPromptDeletion:
    """Test prompt deletion functionality."""
    
    @pytest.fixture
    def prompt_service(self, async_db_session: AsyncSession) -> PromptService:
        """Create PromptService instance."""
        return PromptService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_delete_prompt_success(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test successful prompt deletion."""
        # Create prompt
        prompt = PromptFactory.create_user_prompt(test_user.id)
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        result = await prompt_service.delete_prompt(prompt.id, test_user.id)
        
        assert result == True
        
        # Verify prompt is deleted
        deleted_prompt = await prompt_service.get_prompt_by_id(prompt.id)
        assert deleted_prompt is None
    
    @pytest.mark.asyncio
    async def test_delete_prompt_not_found(
        self, 
        prompt_service: PromptService, 
        test_user
    ):
        """Test deleting non-existent prompt."""
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.delete_prompt(99999, test_user.id)
        
        assert exc_info.value.status_code == 404
        assert "Prompt not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_delete_prompt_wrong_owner(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user,
        test_user_2
    ):
        """Test deleting prompt from different user."""
        # Create prompt for test_user
        prompt = PromptFactory.create_user_prompt(test_user.id)
        async_db_session.add(prompt)
        await async_db_session.commit()
        await async_db_session.refresh(prompt)
        
        with pytest.raises(HTTPException) as exc_info:
            await prompt_service.delete_prompt(prompt.id, test_user_2.id)
        
        assert exc_info.value.status_code == 403
        assert "You can only delete your own prompts" in str(exc_info.value.detail)


class TestPromptSearch:
    """Test prompt search functionality."""
    
    @pytest.fixture
    def prompt_service(self, async_db_session: AsyncSession) -> PromptService:
        """Create PromptService instance."""
        return PromptService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_search_prompts_by_name(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test searching prompts by name."""
        # Create prompts
        prompts = [
            PromptFactory.create_user_prompt(test_user.id, name="meeting_prompt"),
            PromptFactory.create_user_prompt(test_user.id, name="email_prompt"),
            PromptFactory.create_user_prompt(test_user.id, name="document_prompt")
        ]
        
        for prompt in prompts:
            async_db_session.add(prompt)
        
        await async_db_session.commit()
        
        # Search by name
        search_params = PromptSearchParams(name="meeting")
        results, total = await prompt_service.search_prompts(search_params)
        
        assert total == 1
        assert len(results) == 1
        assert results[0].name == "meeting_prompt"
    
    @pytest.mark.asyncio
    async def test_search_prompts_by_type(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test searching prompts by type."""
        # Create prompts
        user_prompt = PromptFactory.create_user_prompt(test_user.id)
        user_prompt.name = "user_prompt"
        async_db_session.add(user_prompt)
        
        admin_prompt = PromptFactory.create_admin_prompt()
        admin_prompt.name = "admin_prompt"
        async_db_session.add(admin_prompt)
        
        await async_db_session.commit()
        
        # Search by type
        search_params = PromptSearchParams(prompt_type="admin")
        results, total = await prompt_service.search_prompts(search_params)
        
        assert total == 1
        assert len(results) == 1
        assert results[0].name == "admin_prompt"
        assert results[0].prompt_type == "admin"
    
    @pytest.mark.asyncio
    async def test_search_prompts_by_user_id(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user,
        test_user_2
    ):
        """Test searching prompts by user ID."""
        # Create prompts for different users
        user1_prompt = PromptFactory.create_user_prompt(test_user.id)
        user1_prompt.name = "user1_prompt"
        async_db_session.add(user1_prompt)
        
        user2_prompt = PromptFactory.create_user_prompt(test_user_2.id)
        user2_prompt.name = "user2_prompt"
        async_db_session.add(user2_prompt)
        
        await async_db_session.commit()
        
        # Search by user ID
        search_params = PromptSearchParams(user_id=test_user.id)
        results, total = await prompt_service.search_prompts(search_params)
        
        assert total == 1
        assert len(results) == 1
        assert results[0].name == "user1_prompt"
        assert results[0].user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_search_prompts_by_active_status(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test searching prompts by active status."""
        # Create prompts
        active_prompt = PromptFactory.create_user_prompt(test_user.id)
        active_prompt.name = "active_prompt"
        active_prompt.is_active = True
        async_db_session.add(active_prompt)
        
        inactive_prompt = PromptFactory.create_user_prompt(test_user.id)
        inactive_prompt.name = "inactive_prompt"
        inactive_prompt.is_active = False
        async_db_session.add(inactive_prompt)
        
        await async_db_session.commit()
        
        # Search by active status
        search_params = PromptSearchParams(is_active=True)
        results, total = await prompt_service.search_prompts(search_params)
        
        assert total == 1
        assert len(results) == 1
        assert results[0].name == "active_prompt"
        assert results[0].is_active == True
    
    @pytest.mark.asyncio
    async def test_search_prompts_pagination(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test prompt search pagination."""
        # Create 5 prompts
        prompts = []
        for i in range(5):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"prompt_{i}"
            async_db_session.add(prompt)
            prompts.append(prompt)
        
        await async_db_session.commit()
        
        # Test pagination
        search_params = PromptSearchParams()
        results, total = await prompt_service.search_prompts(search_params, page=1, limit=2)
        
        assert total == 5
        assert len(results) == 2
        
        # Test second page
        results, total = await prompt_service.search_prompts(search_params, page=2, limit=2)
        
        assert total == 5
        assert len(results) == 2


class TestUserPrompts:
    """Test user-specific prompt operations."""
    
    @pytest.fixture
    def prompt_service(self, async_db_session: AsyncSession) -> PromptService:
        """Create PromptService instance."""
        return PromptService(async_db_session)
    
    @pytest.mark.asyncio
    async def test_get_user_prompts_success(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting user prompts."""
        # Create prompts for user
        prompts = []
        for i in range(3):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"user_prompt_{i}"
            async_db_session.add(prompt)
            prompts.append(prompt)
        
        await async_db_session.commit()
        
        results, total = await prompt_service.get_user_prompts(test_user.id)
        
        assert total == 3
        assert len(results) == 3
        
        for i, prompt in enumerate(results):
            assert prompt.name == f"user_prompt_{i}"
            assert prompt.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_user_prompts_pagination(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test user prompts pagination."""
        # Create 5 prompts
        for i in range(5):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"prompt_{i}"
            async_db_session.add(prompt)
        
        await async_db_session.commit()
        
        # Test pagination
        results, total = await prompt_service.get_user_prompts(test_user.id, page=1, limit=2)
        
        assert total == 5
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_names(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession,
        test_user
    ):
        """Test getting user prompt names."""
        # Create prompts
        prompt_names = ["prompt_1", "prompt_2", "prompt_3"]
        for name in prompt_names:
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = name
            prompt.is_active = True
            async_db_session.add(prompt)
        
        # Create inactive prompt (should not be included)
        inactive_prompt = PromptFactory.create_user_prompt(test_user.id)
        inactive_prompt.name = "inactive_prompt"
        inactive_prompt.is_active = False
        async_db_session.add(inactive_prompt)
        
        await async_db_session.commit()
        
        names = await prompt_service.get_user_prompt_names(test_user.id)
        
        assert len(names) == 3
        assert "prompt_1" in names
        assert "prompt_2" in names
        assert "prompt_3" in names
        assert "inactive_prompt" not in names
    
    @pytest.mark.asyncio
    async def test_get_admin_prompts(
        self, 
        prompt_service: PromptService, 
        async_db_session: AsyncSession
    ):
        """Test getting admin prompts."""
        # Create admin prompts
        admin_prompts = []
        for i in range(2):
            prompt = PromptFactory.create_admin_prompt()
            prompt.name = f"admin_prompt_{i}"
            async_db_session.add(prompt)
            admin_prompts.append(prompt)
        
        # Create user prompt (should not be included)
        user_prompt = PromptFactory.create_user_prompt("user_123")
        user_prompt.name = "user_prompt"
        async_db_session.add(user_prompt)
        
        await async_db_session.commit()
        
        results, total = await prompt_service.get_admin_prompts()
        
        assert total == 2
        assert len(results) == 2
        
        for i, prompt in enumerate(results):
            assert prompt.name == f"admin_prompt_{i}"
            assert prompt.prompt_type == "admin"
            assert prompt.user_id is None
