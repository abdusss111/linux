from fastapi import Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from dapmeet.db.db import SessionLocal, AsyncSessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """
    Provides async database session with guaranteed cleanup.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async session factory is not initialized. Set DATABASE_URL_ASYNC to a valid asyncpg DSN.")
    
    # Use async context manager - это правильный способ для async sessions
    async with AsyncSessionLocal() as session:
        yield session
        # Session автоматически закроется при выходе из async with


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Get the shared HTTP client from app state"""
    return request.app.state.http_client
