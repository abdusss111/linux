from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from dapmeet.core.deps import get_async_db
from dapmeet.services.admin_auth import get_current_admin
from dapmeet.services.prompts import PromptService
from dapmeet.schemas.prompt import (
    PromptCreate, 
    PromptUpdate, 
    PromptResponse, 
    PromptListResponse,
    PromptSearchParams
)

router = APIRouter()


class AdminPromptCreate(BaseModel):
    name: str
    content: str
    is_active: bool = True


@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_prompt(
    prompt_data: AdminPromptCreate,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new admin prompt"""
    prompt_service = PromptService(db)
    
    # Force prompt_type to be admin
    create_data = PromptCreate(
        name=prompt_data.name,
        content=prompt_data.content,
        prompt_type="admin",
        is_active=prompt_data.is_active
    )
    
    prompt = await prompt_service.create_prompt(create_data)
    return prompt


@router.get("/", response_model=PromptListResponse)
async def list_admin_prompts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    name: Optional[str] = Query(None, description="Filter by prompt name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """List admin prompts with pagination and filtering"""
    prompt_service = PromptService(db)
    
    # Build search parameters
    search_params = PromptSearchParams(
        prompt_type="admin",
        name=name,
        is_active=is_active
    )
    
    prompts, total = await prompt_service.search_prompts(search_params, page, limit)
    
    # Calculate pagination metadata
    total_pages = (total + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return PromptListResponse(
        prompts=prompts,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_admin_prompt(
    prompt_id: int,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific admin prompt by ID"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_id(prompt_id)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    return prompt


@router.get("/by-name/{prompt_name}", response_model=PromptResponse)
async def get_admin_prompt_by_name(
    prompt_name: str,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get admin prompt by name"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_name(prompt_name)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    return prompt





@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_admin_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Update an admin prompt"""
    prompt_service = PromptService(db)
    
    # First check if it's an admin prompt
    existing_prompt = await prompt_service.get_prompt_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if existing_prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    prompt = await prompt_service.update_prompt(prompt_id, prompt_data)
    return prompt


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_prompt(
    prompt_id: int,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an admin prompt"""
    prompt_service = PromptService(db)
    
    # First check if it's an admin prompt
    existing_prompt = await prompt_service.get_prompt_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if existing_prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    await prompt_service.delete_prompt(prompt_id)
    return None


@router.get("/stats/count")
async def get_admin_prompts_count(
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get count of admin prompts"""
    prompt_service = PromptService(db)
    prompts, total = await prompt_service.get_admin_prompts(page=1, limit=1)
    return {"total_admin_prompts": total}
