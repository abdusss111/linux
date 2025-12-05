from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from dapmeet.models.prompt import Prompt
from dapmeet.models.user import User
from dapmeet.schemas.prompt import PromptCreate, PromptUpdate, PromptSearchParams
from fastapi import HTTPException, status


class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_prompt(self, prompt_data: PromptCreate, user_id: Optional[str] = None) -> Prompt:
        """Create a new prompt"""
        # Check if name already exists
        existing = await self.db.execute(
            select(Prompt).where(Prompt.name == prompt_data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt with this name already exists"
            )
        
        # Create prompt
        prompt = Prompt(
            name=prompt_data.name,
            content=prompt_data.content,
            prompt_type=prompt_data.prompt_type,
            user_id=user_id,
            is_active=prompt_data.is_active
        )
        
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID"""
        result = await self.db.execute(
            select(Prompt).where(Prompt.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def get_prompt_by_name(self, name: str) -> Optional[Prompt]:
        """Get prompt by name"""
        result = await self.db.execute(
            select(Prompt).where(Prompt.name == name, Prompt.is_active == True)
        )
        return result.scalar_one_or_none()



    async def update_prompt(self, prompt_id: int, prompt_data: PromptUpdate, user_id: Optional[str] = None) -> Prompt:
        """Update an existing prompt"""
        prompt = await self.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        # Check ownership (user can only update their own prompts, admin can update any)
        if user_id and prompt.user_id and prompt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own prompts"
            )
        
        # Check name uniqueness if changing name
        if prompt_data.name and prompt_data.name != prompt.name:
            existing = await self.db.execute(
                select(Prompt).where(Prompt.name == prompt_data.name, Prompt.id != prompt_id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Prompt with this name already exists"
                )
        
        # Update fields
        if prompt_data.name is not None:
            prompt.name = prompt_data.name
        if prompt_data.content is not None:
            prompt.content = prompt_data.content
        if prompt_data.is_active is not None:
            prompt.is_active = prompt_data.is_active
        
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def delete_prompt(self, prompt_id: int, user_id: Optional[str] = None) -> bool:
        """Delete a prompt"""
        prompt = await self.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        # Check ownership
        if user_id and prompt.user_id and prompt.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own prompts"
            )
        
        await self.db.delete(prompt)
        await self.db.commit()
        return True

    async def search_prompts(
        self, 
        search_params: PromptSearchParams,
        page: int = 1,
        limit: int = 50
    ) -> Tuple[List[Prompt], int]:
        """Search prompts with pagination"""
        # Build base query
        base_stmt = select(Prompt).options(selectinload(Prompt.user))
        
        # Apply filters
        conditions = []
        if search_params.name:
            conditions.append(Prompt.name.ilike(f"%{search_params.name}%"))
        if search_params.prompt_type:
            conditions.append(Prompt.prompt_type == search_params.prompt_type)
        if search_params.user_id:
            conditions.append(Prompt.user_id == search_params.user_id)
        if search_params.is_active is not None:
            conditions.append(Prompt.is_active == search_params.is_active)
        
        if conditions:
            base_stmt = base_stmt.where(and_(*conditions))
        
        # Get total count
        total = await self.db.scalar(
            select(func.count()).select_from(base_stmt.subquery())
        )
        
        # Apply pagination
        offset = (page - 1) * limit
        exec_result = await self.db.execute(
            base_stmt.order_by(Prompt.created_at.desc()).offset(offset).limit(limit)
        )
        prompts = exec_result.scalars().all()
        
        return prompts, total

    async def get_user_prompts(self, user_id: str, page: int = 1, limit: int = 50) -> Tuple[List[Prompt], int]:
        """Get prompts owned by a specific user"""
        base_stmt = select(Prompt).where(Prompt.user_id == user_id)
        
        total = await self.db.scalar(
            select(func.count()).select_from(base_stmt.subquery())
        )
        
        offset = (page - 1) * limit
        exec_result = await self.db.execute(
            base_stmt.order_by(Prompt.created_at.desc()).offset(offset).limit(limit)
        )
        prompts = exec_result.scalars().all()
        
        return prompts, total

    async def get_user_prompt_names(self, user_id: str) -> List[str]:
        """Get just the names of user's prompts"""
        result = await self.db.execute(
            select(Prompt.name).where(Prompt.user_id == user_id, Prompt.is_active == True)
        )
        return result.scalars().all()

    async def get_admin_prompts(self, page: int = 1, limit: int = 50) -> Tuple[List[Prompt], int]:
        """Get admin prompts (no user_id)"""
        base_stmt = select(Prompt).where(Prompt.prompt_type == "admin")
        
        total = await self.db.scalar(
            select(func.count()).select_from(base_stmt.subquery())
        )
        
        offset = (page - 1) * limit
        exec_result = await self.db.execute(
            base_stmt.order_by(Prompt.created_at.desc()).offset(offset).limit(limit)
        )
        prompts = exec_result.scalars().all()
        
        return prompts, total
