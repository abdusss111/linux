from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dapmeet.core.deps import get_async_db
from dapmeet.services.auth import get_current_user
from dapmeet.services.subscription import SubscriptionService
from dapmeet.models.user import User
from dapmeet.schemas.subscription import (
    SubscriptionVerificationResponse,
    SubscriptionOut,
    SubscriptionWithHistory
)

router = APIRouter()


@router.get("/verify", response_model=SubscriptionVerificationResponse)
async def verify_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Verify current user's subscription status.
    Returns plan, status, features, and days remaining.
    """
    subscription_service = SubscriptionService(db)
    return await subscription_service.verify_subscription(user.id)

