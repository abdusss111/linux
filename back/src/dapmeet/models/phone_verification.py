# models/phone_verification.py
from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from dapmeet.db.db import Base

class PhoneVerification(Base):
    __tablename__ = "phone_verifications"

    id = Column(String, primary_key=True, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    verification_code = Column(String(6), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
