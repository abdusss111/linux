from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from dapmeet.core.deps import get_async_db
from dapmeet.services.auth import get_current_user
from dapmeet.services.prompts import PromptService
from dapmeet.models.user import User
from dapmeet.schemas.prompt import (
    PromptCreate, 
    PromptUpdate, 
    PromptResponse, 
    PromptListResponse
)

router = APIRouter()


@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_user_prompt(
    prompt_data: PromptCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new user prompt"""
    prompt_service = PromptService(db)
    
    # Force prompt_type to be user and set user_id
    create_data = PromptCreate(
        name=prompt_data.name,
        content=prompt_data.content,
        prompt_type="user",
        is_active=prompt_data.is_active
    )
    
    prompt = await prompt_service.create_prompt(create_data, user_id=current_user.id)
    return prompt


@router.get("/", response_model=PromptListResponse)
async def list_user_prompts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List current user's prompts with pagination"""
    prompt_service = PromptService(db)
    prompts, total = await prompt_service.get_user_prompts(current_user.id, page, limit)
    
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


@router.get("/names", response_model=List[str])
async def get_user_prompt_names(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get just the names of current user's prompts"""
    prompt_service = PromptService(db)
    prompt_names = await prompt_service.get_user_prompt_names(current_user.id)
    return prompt_names


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_user_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific user prompt by ID"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_id(prompt_id)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Check ownership
    if prompt.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return prompt


@router.get("/by-name/{prompt_name}", response_model=PromptResponse)
async def get_user_prompt_by_name(
    prompt_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user prompt by name"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_name(prompt_name)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Check ownership
    if prompt.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_user_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a user prompt"""
    prompt_service = PromptService(db)
    
    # Check ownership first
    existing_prompt = await prompt_service.get_prompt_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if existing_prompt.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    prompt = await prompt_service.update_prompt(prompt_id, prompt_data, user_id=current_user.id)
    return prompt


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a user prompt"""
    prompt_service = PromptService(db)
    
    # Check ownership first
    existing_prompt = await prompt_service.get_prompt_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if existing_prompt.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await prompt_service.delete_prompt(prompt_id, user_id=current_user.id)
    return None


@router.get("/stats/count")
async def get_user_prompts_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get count of current user's prompts"""
    prompt_service = PromptService(db)
    prompts, total = await prompt_service.get_user_prompts(current_user.id, page=1, limit=1)
    return {"total_user_prompts": total}


# ============================================================================
# READ-ONLY ACCESS TO ADMIN PROMPTS FOR REGULAR USERS
# ============================================================================

@router.get("/admin-prompts", response_model=PromptListResponse)
async def get_admin_prompts_readonly(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get admin prompts (read-only access for users)"""
    prompt_service = PromptService(db)
    prompts, total = await prompt_service.get_admin_prompts(page, limit)
    
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


@router.get("/admin-prompts/{prompt_id}", response_model=PromptResponse)
async def get_admin_prompt_readonly(
    prompt_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get admin prompt by ID (read-only access for users)"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_id(prompt_id)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    return prompt


@router.get("/admin-prompts/by-name/{prompt_name}", response_model=PromptResponse)
async def get_admin_prompt_by_name_readonly(
    prompt_name: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get admin prompt by name (read-only access for users)"""
    prompt_service = PromptService(db)
    prompt = await prompt_service.get_prompt_by_name(prompt_name)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt.prompt_type != "admin":
        raise HTTPException(status_code=404, detail="Admin prompt not found")
    
    return prompt


@router.get("/admin-prompts/stats/count")
async def get_admin_prompts_count_readonly(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get count of admin prompts (read-only access for users)"""
    prompt_service = PromptService(db)
    prompts, total = await prompt_service.get_admin_prompts(page=1, limit=1)
    return {"total_admin_prompts": total}
