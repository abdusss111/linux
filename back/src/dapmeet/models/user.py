# models/user.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from dapmeet.db.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # Google ID or phone-based ID
    email = Column(String(255), nullable=True, unique=True, index=True)  # Made nullable for phone auth
    phone_number = Column(String(20), nullable=True, unique=True, index=True)  # Added phone support
    name = Column(String(100), nullable=True)
    auth_provider = Column(String(20), nullable=False, default="google")  # google or phone
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    meetings = relationship(
        "Meeting", back_populates="user",
        cascade="all, delete-orphan"
    )
    
    prompts = relationship(
        "Prompt", back_populates="user",
        cascade="all, delete-orphan"
    )
    
    subscription = relationship(
        "Subscription", back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )