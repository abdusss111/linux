"""
Webhook schemas for external service integration
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class WebhookEmailRequest(BaseModel):
    """Schema for webhook email request"""
    email: EmailStr
    user_name: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class WebhookEmailResponse(BaseModel):
    """Schema for webhook email response"""
    success: bool
    message: str
    email_sent_to: str
    timestamp: str
