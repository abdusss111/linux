from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CodePayload(BaseModel):
    code: str

class PhoneAuthRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number in international format (e.g., +1234567890)")

class PhoneVerificationRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number in international format")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

class PhoneAuthResponse(BaseModel):
    success: bool
    message: str
    verification_id: Optional[str] = None

class PhoneVerificationResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    user: Optional[dict] = None