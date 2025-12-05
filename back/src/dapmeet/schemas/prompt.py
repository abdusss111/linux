from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PromptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Unique name for the prompt")
    content: str = Field(..., min_length=1, description="The prompt content")
    is_active: bool = Field(True, description="Whether the prompt is active")


class PromptCreate(PromptBase):
    prompt_type: str = Field("user", description="Type of prompt: 'admin' or 'user'")


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    endpoint: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class PromptResponse(PromptBase):
    id: int
    prompt_type: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    prompts: List[PromptResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PromptSearchParams(BaseModel):
    name: Optional[str] = None
    prompt_type: Optional[str] = None
    user_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserPromptNamesResponse(BaseModel):
    prompt_names: List[str] 
