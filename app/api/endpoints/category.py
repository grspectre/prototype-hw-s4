from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.security import get_current_user
from app.db.base import User, Category
from app.schemas.product import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.pagination import PaginationParams, PaginatedResponse

router = APIRouter()

@router.get("", response_model=PaginatedResponse[CategoryRead])
async def get_categories(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a paginated list of categories.
    """
    # Count total categories
    count_query = select(func.count()).select_from(Category).where(Category.deleted_at.is_(None))
    total = await db.execute(count_query)
    total_categories = total.scalar()
    
    # Get paginated categories
    offset = (pagination.page - 1) * pagination.page_size
    query = (
        select(Category)
        .where(Category.deleted_at.is_(None))
        .order_by(Category.name)
        .offset(offset)
        .limit(pagination.page_size)
    )
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total_categories + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=categories,
        total=total_categories,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=total_pages
    )

@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new category.
    Requires authentication.
    """
    # Create new category
    category = Category(
        name=category_data.name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(category)
    
    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category_data.name}' already exists"
        )
    
    return category

@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing category.
    Requires authentication.
    """
    # Get the category
    query = select(Category).where(
        Category.category_id == category_id,
        Category.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    
    # Update category attributes
    update_data = category_data.model_dump(exclude_unset=True)
    
    # Only process if there's data to update
    if update_data:
        for key, value in update_data.items():
            setattr(category, key, value)
        
        category.updated_at = datetime.now()
        
        try:
            await db.commit()
            await db.refresh(category)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_data.name}' already exists"
            )
    
    return category

@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific category by ID.
    """
    query = select(Category).where(
        Category.category_id == category_id,
        Category.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a category.
    Requires authentication.
    """
    query = select(Category).where(
        Category.category_id == category_id,
        Category.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    
    # Soft delete
    category.deleted_at = datetime.now()
    await db.commit()
    
    return None