from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dapmeet.services.google_auth_service import JWT_SECRET
from dapmeet.models.user import User
from dapmeet.core.deps import get_async_db
from dapmeet.db.db import AsyncSessionLocal
from dapmeet.services.prompts import PromptService
import jwt
from functools import lru_cache
from datetime import datetime, timedelta

oauth2_scheme = HTTPBearer()

# Simple in-memory cache for user lookups (5 minute TTL)
_user_cache = {}
_cache_ttl = timedelta(minutes=5)

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
):
    """
    Get current user from JWT token.
    Uses short-lived database connection with caching to avoid holding connections.
    
    CRITICAL: This function does NOT use Depends(get_async_db) to avoid 
    the "double depends" pattern that consumes 2 DB connections per request.
    """
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload["sub"]
    
    # Check cache first
    cache_entry = _user_cache.get(user_id)
    if cache_entry:
        cached_user, cached_time = cache_entry
        if datetime.now() - cached_time < _cache_ttl:
            return cached_user
    
    # Cache miss or expired - query database with short-lived connection
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    # Connection automatically closed here
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update cache
    _user_cache[user_id] = (user, datetime.now())
    
    return user


async def get_current_user_with_prompts(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
):
    """
    Get current user with their prompt names included.
    Uses short-lived database connection to avoid connection pool exhaustion.
    
    CRITICAL: Does NOT use Depends(get_async_db) to avoid double-depends pattern.
    """
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload["sub"]
    
    # Short-lived connection for user + prompts lookup
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's prompt names in same short connection
        prompt_service = PromptService(db)
        prompt_names = await prompt_service.get_user_prompt_names(user.id)
    # Connection closed here
    
    # Add prompt_names as a dynamic attribute
    user.prompt_names = prompt_names
    
    return user
