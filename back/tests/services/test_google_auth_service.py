"""
Tests for GoogleAuthService business logic.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
import httpx

from dapmeet.services.google_auth_service import (
    exchange_code_for_token,
    validate_google_access_token,
    get_google_user_info,
    validate_and_get_user_info,
    find_or_create_user,
    generate_jwt,
    authenticate_with_google_token
)


class TestExchangeCodeForToken:
    """Test authorization code to access token exchange."""
    
    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        """Test successful code exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        result = await exchange_code_for_token("mock_code", mock_client)
        
        assert result == "mock_access_token"
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self):
        """Test failed code exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid code"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await exchange_code_for_token("invalid_code", mock_client)
        
        assert exc_info.value.status_code == 400
        assert "Token exchange failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_exchange_code_network_error(self):
        """Test network error during code exchange."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Network error")
        
        with pytest.raises(HTTPException) as exc_info:
            await exchange_code_for_token("mock_code", mock_client)
        
        assert exc_info.value.status_code == 400
        assert "Token exchange failed" in str(exc_info.value.detail)


class TestValidateGoogleAccessToken:
    """Test Google access token validation."""
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test successful token validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audience": "test_client_id",
            "scope": "openid email profile",
            "expires_in": 3600,
            "user_id": "123456789"
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch('dapmeet.services.google_auth_service.GOOGLE_CLIENT_ID', 'test_client_id'):
            result = await validate_google_access_token("mock_token", mock_client)
        
        assert result["audience"] == "test_client_id"
        assert result["expires_in"] == 3600
        mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_token_expired(self):
        """Test validation of expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audience": "test_client_id",
            "expires_in": 0  # Expired
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch('dapmeet.services.google_auth_service.GOOGLE_CLIENT_ID', 'test_client_id'):
            with pytest.raises(HTTPException) as exc_info:
                await validate_google_access_token("expired_token", mock_client)
        
        assert exc_info.value.status_code == 401
        assert "Token has expired" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_token_wrong_audience(self):
        """Test validation of token with wrong audience."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audience": "wrong_client_id",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch('dapmeet.services.google_auth_service.GOOGLE_CLIENT_ID', 'test_client_id'):
            with pytest.raises(HTTPException) as exc_info:
                await validate_google_access_token("wrong_audience_token", mock_client)
        
        assert exc_info.value.status_code == 401
        assert "Token audience mismatch" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_validate_token_extension_audience(self):
        """Test validation of extension token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audience": "extension_client_id",
            "expires_in": 3600
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch('dapmeet.services.google_auth_service.GOOGLE_CLIENT_ID_EXTENSION', 'extension_client_id'):
            with patch('dapmeet.services.google_auth_service.GOOGLE_CLIENT_ID_EXTENSION_PROD', 'extension_prod_client_id'):
                result = await validate_google_access_token("ya29.extension_token", mock_client)
        
        assert result["audience"] == "extension_client_id"
    
    @pytest.mark.asyncio
    async def test_validate_token_api_error(self):
        """Test token validation with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid token"
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_google_access_token("invalid_token", mock_client)
        
        assert exc_info.value.status_code == 401
        assert "Token validation failed" in str(exc_info.value.detail)


class TestGetGoogleUserInfo:
    """Test Google user info retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful user info retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg"
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        result = await get_google_user_info("mock_token", mock_client)
        
        assert result["id"] == "123456789"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test failed user info retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid token"
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await get_google_user_info("invalid_token", mock_client)
        
        assert exc_info.value.status_code == 400
        assert "User info fetch failed" in str(exc_info.value.detail)


class TestValidateAndGetUserInfo:
    """Test combined token validation and user info retrieval."""
    
    @pytest.mark.asyncio
    async def test_validate_and_get_user_info_success(self):
        """Test successful combined validation and user info retrieval."""
        # Mock token validation
        token_info = {
            "audience": "test_client_id",
            "scope": "openid email profile",
            "expires_in": 3600
        }
        
        # Mock user info
        user_info = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        with patch('dapmeet.services.google_auth_service.validate_google_access_token', return_value=token_info) as mock_validate, \
             patch('dapmeet.services.google_auth_service.get_google_user_info', return_value=user_info) as mock_get_info:
            
            mock_client = AsyncMock()
            result = await validate_and_get_user_info("mock_token", mock_client)
        
        assert result["id"] == "123456789"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["token_info"]["audience"] == "test_client_id"
        assert result["token_info"]["expires_in"] == 3600
        
        mock_validate.assert_called_once_with("mock_token", mock_client)
        mock_get_info.assert_called_once_with("mock_token", mock_client)
    
    @pytest.mark.asyncio
    async def test_validate_and_get_user_info_validation_failure(self):
        """Test combined function with validation failure."""
        with patch('dapmeet.services.google_auth_service.validate_google_access_token') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            mock_client = AsyncMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await validate_and_get_user_info("invalid_token", mock_client)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)


class TestFindOrCreateUser:
    """Test user creation and retrieval."""
    
    @pytest.mark.asyncio
    async def test_find_existing_user(self, async_db_session):
        """Test finding existing user."""
        from dapmeet.models.user import User
        
        # Create existing user
        existing_user = User(
            id="123456789",
            email="test@example.com",
            name="Test User",
            auth_provider="google"
        )
        async_db_session.add(existing_user)
        await async_db_session.commit()
        
        user_info = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        result = await find_or_create_user(user_info, async_db_session)
        
        assert result.id == "123456789"
        assert result.email == "test@example.com"
        assert result.name == "Test User"
    
    @pytest.mark.asyncio
    async def test_create_new_user(self, async_db_session, mock_email_service):
        """Test creating new user."""
        user_info = {
            "id": "new_user_123",
            "email": "newuser@example.com",
            "name": "New User"
        }
        
        result = await find_or_create_user(user_info, async_db_session)
        
        assert result.id == "new_user_123"
        assert result.email == "newuser@example.com"
        assert result.name == "New User"
        assert result.auth_provider == "google"
        
        # Verify welcome email was sent
        mock_email_service.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_new_user_email_failure(self, async_db_session, mock_email_service):
        """Test creating new user when email service fails."""
        mock_email_service.side_effect = Exception("Email service down")
        
        user_info = {
            "id": "new_user_123",
            "email": "newuser@example.com",
            "name": "New User"
        }
        
        # Should still create user despite email failure
        result = await find_or_create_user(user_info, async_db_session)
        
        assert result.id == "new_user_123"
        assert result.email == "newuser@example.com"
        assert result.name == "New User"


class TestGenerateJWT:
    """Test JWT token generation."""
    
    def test_generate_jwt_success(self):
        """Test successful JWT generation."""
        user_info = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        with patch('dapmeet.services.google_auth_service.JWT_SECRET', 'test_secret'):
            token = generate_jwt(user_info)
        
        assert isinstance(token, str)
        assert len(token) > 0
        # Token should be a valid JWT (contains dots)
        assert token.count(".") == 2
    
    def test_generate_jwt_with_missing_name(self):
        """Test JWT generation with missing name."""
        user_info = {
            "id": "123456789",
            "email": "test@example.com"
            # Missing name
        }
        
        with patch('dapmeet.services.google_auth_service.JWT_SECRET', 'test_secret'):
            token = generate_jwt(user_info)
        
        assert isinstance(token, str)
        assert len(token) > 0


class TestAuthenticateWithGoogleToken:
    """Test complete Google authentication flow."""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, async_db_session, mock_email_service):
        """Test successful authentication flow."""
        user_info = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "token_info": {
                "audience": "test_client_id",
                "expires_in": 3600
            }
        }
        
        with patch('dapmeet.services.google_auth_service.validate_and_get_user_info', return_value=user_info) as mock_validate, \
             patch('dapmeet.services.google_auth_service.generate_jwt') as mock_generate_jwt:
            
            mock_generate_jwt.return_value = "mock_jwt_token"
            mock_client = AsyncMock()
            
            user, jwt_token = await authenticate_with_google_token("mock_token", async_db_session, mock_client)
        
        assert user.id == "123456789"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert jwt_token == "mock_jwt_token"
        
        mock_validate.assert_called_once_with("mock_token", mock_client)
        mock_generate_jwt.assert_called_once_with(user_info)
    
    @pytest.mark.asyncio
    async def test_authenticate_validation_failure(self, async_db_session):
        """Test authentication with validation failure."""
        with patch('dapmeet.services.google_auth_service.validate_and_get_user_info') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            mock_client = AsyncMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await authenticate_with_google_token("invalid_token", async_db_session, mock_client)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_authenticate_unexpected_error(self, async_db_session):
        """Test authentication with unexpected error."""
        with patch('dapmeet.services.google_auth_service.validate_and_get_user_info') as mock_validate:
            mock_validate.side_effect = Exception("Unexpected error")
            
            mock_client = AsyncMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await authenticate_with_google_token("mock_token", async_db_session, mock_client)
        
        assert exc_info.value.status_code == 500
        assert "Authentication failed" in str(exc_info.value.detail)


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeout."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        
        with pytest.raises(HTTPException) as exc_info:
            await exchange_code_for_token("mock_code", mock_client)
        
        assert exc_info.value.status_code == 400
        assert "Token exchange failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with pytest.raises(HTTPException) as exc_info:
            await exchange_code_for_token("mock_code", mock_client)
        
        assert exc_info.value.status_code == 400
        assert "Token exchange failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_missing_access_token_in_response(self):
        """Test handling of missing access token in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_type": "Bearer",
            "expires_in": 3600
            # Missing access_token
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        
        with pytest.raises(KeyError):
            await exchange_code_for_token("mock_code", mock_client)
    
    @pytest.mark.asyncio
    async def test_user_info_missing_required_fields(self, async_db_session):
        """Test handling of user info with missing required fields."""
        user_info = {
            "id": "123456789"
            # Missing email and name
        }
        
        with pytest.raises(KeyError):
            await find_or_create_user(user_info, async_db_session)
