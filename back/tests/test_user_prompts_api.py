"""
Tests for user prompts API endpoints.
"""
import pytest
from fastapi import status
from httpx import AsyncClient

from tests.factories import PromptFactory, UserFactory


class TestCreateUserPrompt:
    """Test user prompt creation."""
    
    @pytest.mark.asyncio
    async def test_create_user_prompt_success(
        self, 
        async_test_client: AsyncClient, 
        test_user,
        auth_headers: dict
    ):
        """Test successful user prompt creation."""
        prompt_data = {
            "name": "test_prompt",
            "content": "This is a test prompt content",
            "is_active": True
        }
        
        response = await async_test_client.post(
            "/api/prompts/", 
            json=prompt_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["name"] == "test_prompt"
        assert data["content"] == "This is a test prompt content"
        assert data["prompt_type"] == "user"
        assert data["user_id"] == test_user.id
        assert data["is_active"] == True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_create_user_prompt_inactive(
        self, 
        async_test_client: AsyncClient, 
        test_user,
        auth_headers: dict
    ):
        """Test creating inactive user prompt."""
        prompt_data = {
            "name": "inactive_prompt",
            "content": "This is an inactive prompt",
            "is_active": False
        }
        
        response = await async_test_client.post(
            "/api/prompts/", 
            json=prompt_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["name"] == "inactive_prompt"
        assert data["is_active"] == False
        assert data["prompt_type"] == "user"
        assert data["user_id"] == test_user.id
    
    @pytest.mark.asyncio
    async def test_create_user_prompt_validation_error(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test creating user prompt with invalid data."""
        # Missing required fields
        response = await async_test_client.post(
            "/api/prompts/", 
            json={}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing name
        response = await async_test_client.post(
            "/api/prompts/", 
            json={"content": "Test content"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing content
        response = await async_test_client.post(
            "/api/prompts/", 
            json={"name": "test_prompt"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Empty name
        response = await async_test_client.post(
            "/api/prompts/", 
            json={"name": "", "content": "Test content"}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Empty content
        response = await async_test_client.post(
            "/api/prompts/", 
            json={"name": "test_prompt", "content": ""}, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_create_user_prompt_duplicate_name(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test creating user prompt with duplicate name."""
        # Create initial prompt
        existing_prompt = PromptFactory.create_user_prompt(test_user.id)
        existing_prompt.name = "duplicate_name"
        async_db_session.add(existing_prompt)
        await async_db_session.commit()
        
        # Try to create prompt with same name
        prompt_data = {
            "name": "duplicate_name",
            "content": "Different content",
            "is_active": True
        }
        
        response = await async_test_client.post(
            "/api/prompts/", 
            json=prompt_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Prompt with this name already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_user_prompt_unauthorized(
        self, 
        async_test_client: AsyncClient
    ):
        """Test creating user prompt without authentication."""
        prompt_data = {
            "name": "test_prompt",
            "content": "Test content",
            "is_active": True
        }
        
        response = await async_test_client.post(
            "/api/prompts/", 
            json=prompt_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListUserPrompts:
    """Test user prompt listing with pagination."""
    
    @pytest.mark.asyncio
    async def test_list_user_prompts_empty(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test listing prompts when user has no prompts."""
        response = await async_test_client.get("/api/prompts/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["prompts"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["limit"] == 50
        assert data["total_pages"] == 0
        assert data["has_next"] == False
        assert data["has_prev"] == False
    
    @pytest.mark.asyncio
    async def test_list_user_prompts_with_data(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test listing prompts with existing data."""
        # Create test prompts
        prompts = []
        for i in range(3):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"prompt_{i}"
            prompt.content = f"Content {i}"
            async_db_session.add(prompt)
            prompts.append(prompt)
        
        await async_db_session.commit()
        
        response = await async_test_client.get("/api/prompts/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["prompts"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["limit"] == 50
        assert data["total_pages"] == 1
        assert data["has_next"] == False
        assert data["has_prev"] == False
        
        # Verify prompt data
        for i, prompt_data in enumerate(data["prompts"]):
            assert prompt_data["name"] == f"prompt_{i}"
            assert prompt_data["content"] == f"Content {i}"
            assert prompt_data["user_id"] == test_user.id
            assert prompt_data["prompt_type"] == "user"
    
    @pytest.mark.asyncio
    async def test_list_user_prompts_pagination(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test user prompt pagination."""
        # Create 5 test prompts
        prompts = []
        for i in range(5):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"prompt_{i}"
            async_db_session.add(prompt)
            prompts.append(prompt)
        
        await async_db_session.commit()
        
        # Test first page
        response = await async_test_client.get(
            "/api/prompts/?page=1&limit=2", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["prompts"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["total_pages"] == 3
        assert data["has_next"] == True
        assert data["has_prev"] == False
        
        # Test second page
        response = await async_test_client.get(
            "/api/prompts/?page=2&limit=2", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["prompts"]) == 2
        assert data["page"] == 2
        assert data["has_next"] == True
        assert data["has_prev"] == True
        
        # Test last page
        response = await async_test_client.get(
            "/api/prompts/?page=3&limit=2", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["prompts"]) == 1
        assert data["page"] == 3
        assert data["has_next"] == False
        assert data["has_prev"] == True
    
    @pytest.mark.asyncio
    async def test_list_user_prompts_only_user_prompts(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test that only user's own prompts are returned."""
        # Create user prompt
        user_prompt = PromptFactory.create_user_prompt(test_user.id)
        user_prompt.name = "user_prompt"
        async_db_session.add(user_prompt)
        
        # Create admin prompt
        admin_prompt = PromptFactory.create_admin_prompt()
        admin_prompt.name = "admin_prompt"
        async_db_session.add(admin_prompt)
        
        # Create prompt for different user
        other_user = UserFactory.create()
        async_db_session.add(other_user)
        await async_db_session.commit()
        
        other_prompt = PromptFactory.create_user_prompt(other_user.id)
        other_prompt.name = "other_user_prompt"
        async_db_session.add(other_prompt)
        
        await async_db_session.commit()
        
        response = await async_test_client.get("/api/prompts/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return user's own prompt
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["name"] == "user_prompt"
        assert data["prompts"][0]["user_id"] == test_user.id


class TestGetUserPromptNames:
    """Test getting user prompt names."""
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_names_empty(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting prompt names when user has no prompts."""
        response = await async_test_client.get("/api/prompts/names", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data == []
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_names_with_data(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test getting prompt names with existing prompts."""
        # Create test prompts
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
        
        response = await async_test_client.get("/api/prompts/names", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return active prompts
        assert len(data) == 3
        assert "prompt_1" in data
        assert "prompt_2" in data
        assert "prompt_3" in data
        assert "inactive_prompt" not in data


class TestGetUserPrompt:
    """Test getting individual user prompts."""
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_success(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test successful user prompt retrieval."""
        response = await async_test_client.get(
            f"/api/prompts/{test_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_prompt.id
        assert data["name"] == test_prompt.name
        assert data["content"] == test_prompt.content
        assert data["prompt_type"] == "user"
        assert data["user_id"] == test_prompt.user_id
        assert data["is_active"] == test_prompt.is_active
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting non-existent user prompt."""
        response = await async_test_client.get(
            "/api/prompts/99999", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Prompt not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_wrong_owner(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user_2,
        auth_headers: dict
    ):
        """Test getting prompt from different user."""
        # Create prompt for different user
        other_prompt = PromptFactory.create_user_prompt(test_user_2.id)
        async_db_session.add(other_prompt)
        await async_db_session.commit()
        await async_db_session.refresh(other_prompt)
        
        response = await async_test_client.get(
            f"/api/prompts/{other_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_by_name_success(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test successful user prompt retrieval by name."""
        response = await async_test_client.get(
            f"/api/prompts/by-name/{test_prompt.name}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_prompt.id
        assert data["name"] == test_prompt.name
        assert data["content"] == test_prompt.content
    
    @pytest.mark.asyncio
    async def test_get_user_prompt_by_name_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting user prompt by non-existent name."""
        response = await async_test_client.get(
            "/api/prompts/by-name/nonexistent_prompt", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Prompt not found" in response.json()["detail"]


class TestUpdateUserPrompt:
    """Test updating user prompts."""
    
    @pytest.mark.asyncio
    async def test_update_user_prompt_success(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test successful user prompt update."""
        update_data = {
            "name": "updated_prompt_name",
            "content": "Updated prompt content",
            "is_active": False
        }
        
        response = await async_test_client.put(
            f"/api/prompts/{test_prompt.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_prompt.id
        assert data["name"] == "updated_prompt_name"
        assert data["content"] == "Updated prompt content"
        assert data["is_active"] == False
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_update_user_prompt_partial(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test partial user prompt update."""
        update_data = {
            "content": "Only content updated"
        }
        
        response = await async_test_client.put(
            f"/api/prompts/{test_prompt.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_prompt.id
        assert data["name"] == test_prompt.name  # Should remain unchanged
        assert data["content"] == "Only content updated"
        assert data["is_active"] == test_prompt.is_active  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_update_user_prompt_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test updating non-existent user prompt."""
        update_data = {
            "content": "Updated content"
        }
        
        response = await async_test_client.put(
            "/api/prompts/99999", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Prompt not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_user_prompt_wrong_owner(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user_2,
        auth_headers: dict
    ):
        """Test updating prompt from different user."""
        # Create prompt for different user
        other_prompt = PromptFactory.create_user_prompt(test_user_2.id)
        async_db_session.add(other_prompt)
        await async_db_session.commit()
        await async_db_session.refresh(other_prompt)
        
        update_data = {
            "content": "Updated content"
        }
        
        response = await async_test_client.put(
            f"/api/prompts/{other_prompt.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_user_prompt_duplicate_name(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
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
        
        # Try to update prompt2 with prompt1's name
        update_data = {
            "name": "prompt_1"
        }
        
        response = await async_test_client.put(
            f"/api/prompts/{prompt2.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Prompt with this name already exists" in response.json()["detail"]


class TestDeleteUserPrompt:
    """Test deleting user prompts."""
    
    @pytest.mark.asyncio
    async def test_delete_user_prompt_success(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test successful user prompt deletion."""
        response = await async_test_client.delete(
            f"/api/prompts/{test_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify prompt is deleted
        response = await async_test_client.get(
            f"/api/prompts/{test_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_user_prompt_not_found(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test deleting non-existent user prompt."""
        response = await async_test_client.delete(
            "/api/prompts/99999", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Prompt not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_user_prompt_wrong_owner(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user_2,
        auth_headers: dict
    ):
        """Test deleting prompt from different user."""
        # Create prompt for different user
        other_prompt = PromptFactory.create_user_prompt(test_user_2.id)
        async_db_session.add(other_prompt)
        await async_db_session.commit()
        await async_db_session.refresh(other_prompt)
        
        response = await async_test_client.delete(
            f"/api/prompts/{other_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied" in response.json()["detail"]


class TestGetUserPromptsCount:
    """Test getting user prompts count."""
    
    @pytest.mark.asyncio
    async def test_get_user_prompts_count_empty(
        self, 
        async_test_client: AsyncClient, 
        auth_headers: dict
    ):
        """Test getting count when user has no prompts."""
        response = await async_test_client.get(
            "/api/prompts/stats/count", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_user_prompts"] == 0
    
    @pytest.mark.asyncio
    async def test_get_user_prompts_count_with_data(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_user,
        auth_headers: dict
    ):
        """Test getting count with existing prompts."""
        # Create test prompts
        for i in range(3):
            prompt = PromptFactory.create_user_prompt(test_user.id)
            prompt.name = f"prompt_{i}"
            async_db_session.add(prompt)
        
        await async_db_session.commit()
        
        response = await async_test_client.get(
            "/api/prompts/stats/count", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_user_prompts"] == 3


class TestAdminPromptsReadOnly:
    """Test read-only access to admin prompts."""
    
    @pytest.mark.asyncio
    async def test_get_admin_prompts_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_admin_prompt,
        auth_headers: dict
    ):
        """Test successful admin prompts retrieval."""
        response = await async_test_client.get(
            "/api/prompts/admin-prompts", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["prompts"]) == 1
        assert data["prompts"][0]["name"] == test_admin_prompt.name
        assert data["prompts"][0]["prompt_type"] == "admin"
        assert data["prompts"][0]["user_id"] is None
    
    @pytest.mark.asyncio
    async def test_get_admin_prompt_by_id_success(
        self, 
        async_test_client: AsyncClient, 
        test_admin_prompt,
        auth_headers: dict
    ):
        """Test successful admin prompt retrieval by ID."""
        response = await async_test_client.get(
            f"/api/prompts/admin-prompts/{test_admin_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_admin_prompt.id
        assert data["name"] == test_admin_prompt.name
        assert data["prompt_type"] == "admin"
        assert data["user_id"] is None
    
    @pytest.mark.asyncio
    async def test_get_admin_prompt_by_name_success(
        self, 
        async_test_client: AsyncClient, 
        test_admin_prompt,
        auth_headers: dict
    ):
        """Test successful admin prompt retrieval by name."""
        response = await async_test_client.get(
            f"/api/prompts/admin-prompts/by-name/{test_admin_prompt.name}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_admin_prompt.id
        assert data["name"] == test_admin_prompt.name
        assert data["prompt_type"] == "admin"
    
    @pytest.mark.asyncio
    async def test_get_admin_prompt_not_admin_type(
        self, 
        async_test_client: AsyncClient, 
        test_prompt,
        auth_headers: dict
    ):
        """Test getting user prompt as admin prompt."""
        response = await async_test_client.get(
            f"/api/prompts/admin-prompts/{test_prompt.id}", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Admin prompt not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_admin_prompts_count(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        test_admin_prompt,
        auth_headers: dict
    ):
        """Test getting admin prompts count."""
        response = await async_test_client.get(
            "/api/prompts/admin-prompts/stats/count", 
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total_admin_prompts"] == 1
