from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class ChatMessageBase(BaseModel):
    sender: str = Field(..., min_length=1, max_length=50, description="Message sender identifier")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message"""
    pass


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response"""
    id: int = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Meeting session identifier")
    created_at: datetime = Field(..., description="Message creation timestamp")

    class Config:
        from_attributes = True


class ChatHistoryBulkRequest(BaseModel):
    """Schema for bulk chat history operations"""
    session_id: str = Field(..., description="Meeting session identifier")
    messages: List[ChatMessageCreate] = Field(
        ..., 
        min_items=1, 
        max_items=1000,
        description="List of messages to save"
    )

    @validator('messages')
    def validate_messages_not_empty(cls, v):
        if not v:
            raise ValueError('Messages list cannot be empty')
        return v


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""
    session_id: str
    total_messages: int
    messages: List[ChatMessageResponse]


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(50, ge=1, le=100, description="Page size")
