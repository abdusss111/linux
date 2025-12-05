from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta, timezone
from dapmeet.models.subscription import Subscription, SubscriptionHistory, SubscriptionPlan, SubscriptionStatus
from dapmeet.models.user import User
from dapmeet.schemas.subscription import (
    SubscriptionOut, 
    SubscriptionVerificationResponse, 
    SubscriptionUpdate,
    PLAN_FEATURES
)
from fastapi import HTTPException, status


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_subscription(self, user_id: str) -> Subscription:
        """Get existing subscription or create a premium one for the user (PRO users)"""
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            # Create premium subscription by default (PRO users)
            # Use .value to ensure lowercase string is saved to database
            subscription = Subscription(
                user_id=user_id,
                plan=SubscriptionPlan.PREMIUM.value,  # Explicitly use .value
                status=SubscriptionStatus.ACTIVE.value,  # Explicitly use .value
                start_date=datetime.now(timezone.utc)
            )
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            
            # Create initial history entry
            await self._create_history_entry(
                subscription,
                None,
                SubscriptionPlan.PREMIUM,
                None,
                SubscriptionStatus.ACTIVE,
                None,
                "Initial premium subscription (PRO user)"
            )
        
        return subscription

    async def get_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get subscription for a user"""
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_with_history(self, user_id: str) -> Optional[Subscription]:
        """Get subscription with history loaded"""
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.history))
            .where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def verify_subscription(self, user_id: str) -> SubscriptionVerificationResponse:
        """Verify subscription and return current plan, status, and features"""
        subscription = await self.get_or_create_subscription(user_id)
        
        features = PLAN_FEATURES[subscription.plan.value]
        
        # Calculate days remaining (None for free plan)
        days_remaining = None
        if subscription.end_date:
            now = datetime.now(timezone.utc)
            if subscription.end_date > now:
                days_remaining = (subscription.end_date - now).days
            else:
                days_remaining = 0
        
        return SubscriptionVerificationResponse(
            plan=subscription.plan.value,
            status=subscription.status.value,
            features=features,
            days_remaining=days_remaining
        )

    async def update_subscription(
        self, 
        user_id: str, 
        update_data: SubscriptionUpdate,
        changed_by: Optional[str] = None
    ) -> Subscription:
        """Update user subscription (admin only)"""
        subscription = await self.get_or_create_subscription(user_id)
        
        old_plan = subscription.plan
        old_status = subscription.status
        
        # Update plan if provided
        if update_data.plan is not None:
            subscription.plan = update_data.plan
            
            # Set end_date for paid plans (30 days from now or extend existing)
            if update_data.plan != SubscriptionPlan.FREE:
                if subscription.end_date and update_data.extend_days:
                    # Extend existing subscription
                    subscription.end_date = subscription.end_date + timedelta(days=update_data.extend_days)
                elif not subscription.end_date or subscription.end_date < datetime.now(timezone.utc):
                    # New subscription or expired - start fresh
                    subscription.start_date = datetime.now(timezone.utc)
                    subscription.end_date = datetime.now(timezone.utc) + timedelta(days=30)
                # If subscription is still active, keep existing end_date unless extending
            else:
                # Downgrade to free - clear end_date
                subscription.end_date = None
        
        # Update status if provided
        if update_data.status is not None:
            subscription.status = update_data.status
        
        # Update last_updated timestamp
        subscription.last_updated = datetime.now(timezone.utc)
        
        # Create history entry
        await self._create_history_entry(
            subscription,
            old_plan,
            subscription.plan,
            old_status,
            subscription.status,
            changed_by,
            update_data.reason
        )
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        return subscription

    async def _create_history_entry(
        self,
        subscription: Subscription,
        old_plan: Optional[SubscriptionPlan],
        new_plan: SubscriptionPlan,
        old_status: Optional[SubscriptionStatus],
        new_status: SubscriptionStatus,
        changed_by: Optional[str],
        reason: Optional[str]
    ) -> None:
        """Create a history entry for subscription changes"""
        history_entry = SubscriptionHistory(
            subscription_id=subscription.id,
            old_plan=old_plan,
            new_plan=new_plan,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason
        )
        self.db.add(history_entry)
        await self.db.commit()

    def get_subscription_features(self, plan: SubscriptionPlan) -> dict:
        """Get features for a subscription plan"""
        return PLAN_FEATURES[plan.value]

    def can_use_action_buttons(self, subscription: Subscription) -> bool:
        """Check if user can use AI action buttons (not available for free plan)"""
        return subscription.plan != SubscriptionPlan.FREE and subscription.status == SubscriptionStatus.ACTIVE

