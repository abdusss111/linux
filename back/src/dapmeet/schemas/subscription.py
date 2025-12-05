from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from dapmeet.models.subscription import SubscriptionPlan, SubscriptionStatus


class SubscriptionFeatures(BaseModel):
    """Features available for each subscription plan"""
    platforms: List[str]
    transcript_storage: str
    transcription_mode: str
    ai_capabilities: str
    export_formats: List[str]


class SubscriptionOut(BaseModel):
    """Subscription response schema"""
    id: int
    user_id: str
    plan: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    last_updated: datetime
    created_at: datetime
    features: SubscriptionFeatures
    
    class Config:
        from_attributes = True


class SubscriptionVerificationResponse(BaseModel):
    """Response for subscription verification endpoint"""
    plan: str
    status: str
    features: SubscriptionFeatures
    days_remaining: Optional[int] = None  # None for free plan


class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription (admin only)"""
    plan: Optional[SubscriptionPlan] = None
    status: Optional[SubscriptionStatus] = None
    extend_days: Optional[int] = Field(None, ge=1, description="Extend subscription by N days")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the change")


class SubscriptionHistoryOut(BaseModel):
    """Subscription history entry"""
    id: int
    subscription_id: int
    old_plan: Optional[str] = None
    new_plan: str
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    reason: Optional[str] = None
    changed_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionWithHistory(BaseModel):
    """Subscription with full history"""
    subscription: SubscriptionOut
    history: List[SubscriptionHistoryOut]


# Feature definitions for each plan
PLAN_FEATURES: Dict[str, SubscriptionFeatures] = {
    SubscriptionPlan.FREE.value: SubscriptionFeatures(
        platforms=["Google Meet"],
        transcript_storage="7 days",
        transcription_mode="⚠️ Notification to other meeting participants",
        ai_capabilities="Limited (chat only)",
        export_formats=[]
    ),
    SubscriptionPlan.STANDARD.value: SubscriptionFeatures(
        platforms=["Google Meet"],
        transcript_storage="Unlimited",
        transcription_mode="✅ Silent Mode",
        ai_capabilities="Full (with action buttons)",
        export_formats=["TXT"]
    ),
    SubscriptionPlan.PREMIUM.value: SubscriptionFeatures(
        platforms=["Google Meet"],
        transcript_storage="Unlimited",
        transcription_mode="✅ Silent Mode",
        ai_capabilities="Full (with action buttons)",
        export_formats=["TXT"]  # Placeholder - will be expanded later
    )
}

