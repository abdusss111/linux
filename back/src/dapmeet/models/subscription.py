# models/subscription.py
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, TypeDecorator
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from dapmeet.db.db import Base
import enum

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SubscriptionPlanEnum(TypeDecorator):
    """TypeDecorator to ensure enum values are used instead of names"""
    impl = postgresql.ENUM('free', 'standard', 'premium', name='subscriptionplan', create_type=False)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Convert enum to its value (lowercase string)
        if isinstance(value, SubscriptionPlan):
            return value.value
        # If it's already a string, ensure it's lowercase
        if isinstance(value, str):
            return value.lower()
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, SubscriptionPlan):
            return value
        return SubscriptionPlan(value.lower())

class SubscriptionStatusEnum(TypeDecorator):
    """TypeDecorator to ensure enum values are used instead of names"""
    impl = postgresql.ENUM('active', 'expired', 'cancelled', name='subscriptionstatus', create_type=False)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Convert enum to its value (lowercase string)
        if isinstance(value, SubscriptionStatus):
            return value.value
        # If it's already a string, ensure it's lowercase
        if isinstance(value, str):
            return value.lower()
        return str(value).lower()
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, SubscriptionStatus):
            return value
        return SubscriptionStatus(value.lower())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan = Column(SubscriptionPlanEnum(), nullable=False, default=SubscriptionPlan.FREE.value, index=True)
    status = Column(SubscriptionStatusEnum(), nullable=False, default=SubscriptionStatus.ACTIVE.value, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)  # NULL for free plan
    last_updated = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="subscription")
    history = relationship(
        "SubscriptionHistory", 
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionHistory.changed_at.desc()"
    )

class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    old_plan = Column(SubscriptionPlanEnum(), nullable=True)
    new_plan = Column(SubscriptionPlanEnum(), nullable=False)
    old_status = Column(SubscriptionStatusEnum(), nullable=True)
    new_status = Column(SubscriptionStatusEnum(), nullable=False)
    changed_by = Column(String, nullable=True)  # Admin user ID who made the change
    reason = Column(String(500), nullable=True)  # Optional reason/notes
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    subscription = relationship("Subscription", back_populates="history")

