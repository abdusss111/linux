"""
Tests for authentication API endpoints.
"""
import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from tests.factories import UserFactory


class TestGoogleAuth:
    """Test Google OAuth authentication flow."""
    
    @pytest.mark.asyncio
    async def test_google_auth_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test successful Google OAuth authentication."""
        # Mock Google OAuth responses
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].return_value = {
            "id": "google_user_123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["id"] == "google_user_123"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["name"] == "Test User"
        
        # Verify mocks were called
        mock_google_auth["exchange"].assert_called_once_with("mock_auth_code", mock_google_auth["exchange"].call_args[0][1])
        mock_google_auth["user_info"].assert_called_once()
        mock_email_service.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_google_auth_existing_user(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test Google OAuth with existing user (no welcome email)."""
        # Create existing user
        existing_user = UserFactory.create(
            id="google_user_123",
            email="test@example.com",
            name="Existing User"
        )
        async_db_session.add(existing_user)
        await async_db_session.commit()
        
        # Mock Google OAuth responses
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].return_value = {
            "id": "google_user_123",
            "email": "test@example.com",
            "name": "Existing User"
        }
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["id"] == "google_user_123"
        
        # Verify welcome email was NOT sent for existing user
        mock_email_service.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_google_auth_invalid_code(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Google OAuth with invalid authorization code."""
        # Mock failed token exchange
        mock_google_auth["exchange"].side_effect = Exception("Invalid code")
        
        # Test data
        auth_data = {"code": "invalid_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token exchange failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_google_auth_missing_code(
        self, 
        async_test_client: AsyncClient
    ):
        """Test Google OAuth with missing authorization code."""
        # Test data without code
        auth_data = {}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestChromeExtensionAuth:
    """Test Chrome extension authentication validation."""
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_success(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test successful Chrome extension authentication."""
        # Mock Google token validation
        mock_google_auth["validate"].return_value = {
            "audience": "test_extension_client_id",
            "expires_in": 3600
        }
        mock_google_auth["user_info"].return_value = {
            "id": "extension_user_123",
            "email": "extension@example.com",
            "name": "Extension User"
        }
        
        # Make request with Bearer token
        headers = {"Authorization": "Bearer mock_extension_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["id"] == "extension_user_123"
        assert data["user"]["email"] == "extension@example.com"
        assert data["user"]["name"] == "Extension User"
        
        # Verify mocks were called
        mock_google_auth["validate"].assert_called_once()
        mock_google_auth["user_info"].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_missing_header(
        self, 
        async_test_client: AsyncClient
    ):
        """Test Chrome extension auth with missing Authorization header."""
        # Make request without Authorization header
        response = await async_test_client.post("/auth/validate")
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing or invalid auth header" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_invalid_header_format(
        self, 
        async_test_client: AsyncClient
    ):
        """Test Chrome extension auth with invalid header format."""
        # Make request with invalid header format
        headers = {"Authorization": "InvalidFormat mock_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing or invalid auth header" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_invalid_token(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Chrome extension auth with invalid token."""
        # Mock failed token validation
        mock_google_auth["validate"].side_effect = Exception("Invalid token")
        
        # Make request with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token validation failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_expired_token(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Chrome extension auth with expired token."""
        # Mock expired token
        mock_google_auth["validate"].return_value = {
            "audience": "test_extension_client_id",
            "expires_in": 0  # Expired
        }
        
        # Make request with expired token
        headers = {"Authorization": "Bearer expired_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token has expired" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_wrong_audience(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Chrome extension auth with wrong audience."""
        # Mock wrong audience
        mock_google_auth["validate"].return_value = {
            "audience": "wrong_client_id",
            "expires_in": 3600
        }
        
        # Make request with wrong audience token
        headers = {"Authorization": "Bearer wrong_audience_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token audience mismatch" in response.json()["detail"]


class TestJWTTokenHandling:
    """Test JWT token generation and validation."""
    
    @pytest.mark.asyncio
    async def test_jwt_token_structure(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test that generated JWT tokens have correct structure."""
        # Mock Google OAuth responses
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].return_value = {
            "id": "jwt_test_user",
            "email": "jwt@example.com",
            "name": "JWT Test User"
        }
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify JWT token is present and is a string
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        
        # Token should be a valid JWT (contains dots)
        assert data["access_token"].count(".") == 2
    
    @pytest.mark.asyncio
    async def test_jwt_token_contains_user_info(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test that JWT token contains correct user information."""
        # Mock Google OAuth responses
        user_info = {
            "id": "jwt_user_123",
            "email": "jwt@example.com",
            "name": "JWT User"
        }
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].return_value = user_info
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify user info in response matches input
        assert data["user"]["id"] == user_info["id"]
        assert data["user"]["email"] == user_info["email"]
        assert data["user"]["name"] == user_info["name"]


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_google_auth_network_error(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Google OAuth with network error."""
        # Mock network error
        mock_google_auth["exchange"].side_effect = Exception("Network error")
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token exchange failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_google_auth_invalid_user_info(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Google OAuth with invalid user info response."""
        # Mock successful token exchange but invalid user info
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].side_effect = Exception("Invalid user info")
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "User info fetch failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_chrome_extension_auth_network_error(
        self, 
        async_test_client: AsyncClient, 
        mock_google_auth
    ):
        """Test Chrome extension auth with network error."""
        # Mock network error
        mock_google_auth["validate"].side_effect = Exception("Network error")
        
        # Make request
        headers = {"Authorization": "Bearer mock_token"}
        response = await async_test_client.post("/auth/validate", headers=headers)
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token validation failed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_email_service_failure_does_not_break_auth(
        self, 
        async_test_client: AsyncClient, 
        async_db_session,
        mock_google_auth,
        mock_email_service
    ):
        """Test that email service failure doesn't break authentication."""
        # Mock Google OAuth responses
        mock_google_auth["exchange"].return_value = "mock_access_token"
        mock_google_auth["user_info"].return_value = {
            "id": "email_test_user",
            "email": "email@example.com",
            "name": "Email Test User"
        }
        
        # Mock email service failure
        mock_email_service.side_effect = Exception("Email service down")
        
        # Test data
        auth_data = {"code": "mock_auth_code"}
        
        # Make request
        response = await async_test_client.post("/auth/google", json=auth_data)
        
        # Assertions - auth should still succeed despite email failure
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["user"]["id"] == "email_test_user"
    
    @pytest.mark.asyncio
    async def test_malformed_json_request(
        self, 
        async_test_client: AsyncClient
    ):
        """Test authentication with malformed JSON."""
        # Make request with malformed JSON
        response = await async_test_client.post(
            "/auth/google", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_empty_request_body(
        self, 
        async_test_client: AsyncClient
    ):
        """Test authentication with empty request body."""
        # Make request with empty body
        response = await async_test_client.post("/auth/google", json={})
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
