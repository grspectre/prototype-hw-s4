from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.security import get_current_user
from app.db.base import User, Product, Category
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, ProductDetailRead
from app.schemas.pagination import PaginationParams, PaginatedResponse

router = APIRouter()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new product.
    Requires authentication.
    """
    # Check if the category exists
    category_query = select(Category).where(Category.category_id == product_data.category_id)
    category = await db.execute(category_query)
    category = category.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {product_data.category_id} not found"
        )
    
    # Create new product
    new_product = Product(**product_data.model_dump())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    
    return new_product


@router.get("", response_model=PaginatedResponse[ProductRead])
async def list_products(
    name: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    category_id: Optional[UUID] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a paginated list of products with optional filtering.
    """
    # Build the base query
    query = select(Product).where(Product.deleted_at.is_(None))
    count_query = select(func.count()).select_from(Product).where(Product.deleted_at.is_(None))
    
    # Apply filters if provided
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))
        count_query = count_query.filter(Product.name.ilike(f"%{name}%"))
        
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
        count_query = count_query.filter(Product.price >= min_price)
        
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
        count_query = count_query.filter(Product.price <= max_price)
        
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)
        count_query = count_query.filter(Product.rating >= min_rating)
        
    if category_id:
        query = query.filter(Product.category_id == category_id)
        count_query = count_query.filter(Product.category_id == category_id)
    
    # Calculate pagination
    total = await db.execute(count_query)
    total = total.scalar()
    
    # Calculate offset and limit based on pagination params
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=products,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=total_pages
    )


@router.get("/search", response_model=PaginatedResponse[ProductRead])
async def search_products(
    query: str = Query(..., min_length=1),
    category_id: Optional[UUID] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Search products by name with optional filtering.
    """
    # Build the base query
    search_query = select(Product).where(
        Product.name.ilike(f"%{query}%"),
        Product.deleted_at.is_(None)
    )
    
    count_query = select(func.count()).select_from(Product).where(
        Product.name.ilike(f"%{query}%"),
        Product.deleted_at.is_(None)
    )
    
    # Apply filters if provided
    if category_id:
        search_query = search_query.filter(Product.category_id == category_id)
        count_query = count_query.filter(Product.category_id == category_id)
        
    if min_price is not None:
        search_query = search_query.filter(Product.price >= min_price)
        count_query = count_query.filter(Product.price >= min_price)
        
    if max_price is not None:
        search_query = search_query.filter(Product.price <= max_price)
        count_query = count_query.filter(Product.price <= max_price)
        
    if min_rating is not None:
        search_query = search_query.filter(Product.rating >= min_rating)
        count_query = count_query.filter(Product.rating >= min_rating)
    
    # Calculate pagination
    total = await db.execute(count_query)
    total = total.scalar()
    
    # Calculate offset and limit based on pagination params
    offset = (pagination.page - 1) * pagination.page_size
    search_query = search_query.offset(offset).limit(pagination.page_size)
    
    # Execute query
    result = await db.execute(search_query)
    products = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=products,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=total_pages
    )


@router.get("/{product_id}", response_model=ProductDetailRead)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve detailed information about a specific product.
    """
    query = select(Product).options(selectinload(Product.category)).where(
        Product.product_id == product_id,
        Product.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    return product


@router.get("/category/{category_id}", response_model=PaginatedResponse[ProductRead])
async def list_products_by_category(
    category_id: UUID,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a paginated list of products in a specific category.
    """
    # Check if the category exists
    category_query = select(Category).where(
        Category.category_id == category_id,
        Category.deleted_at.is_(None)
    )
    category = await db.execute(category_query)
    category = category.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    
    # Build the base query for products in this category
    query = select(Product).where(
        Product.category_id == category_id,
        Product.deleted_at.is_(None)
    )
    
    count_query = select(func.count()).select_from(Product).where(
        Product.category_id == category_id,
        Product.deleted_at.is_(None)
    )
    
    # Apply filters if provided
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
        count_query = count_query.filter(Product.price >= min_price)
        
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
        count_query = count_query.filter(Product.price <= max_price)
        
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)
        count_query = count_query.filter(Product.rating >= min_rating)
    
    # Calculate pagination
    total = await db.execute(count_query)
    total = total.scalar()
    
    # Calculate offset and limit based on pagination params
    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)
    
    # Execute query
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Calculate total pages
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=products,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=total_pages
    )


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing product.
    Requires authentication.
    """
    # Get the product
    query = select(Product).where(
        Product.product_id == product_id,
        Product.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Check if category_id is being updated and whether the new category exists
    if product_data.category_id is not None and product_data.category_id != product.category_id:
        category_query = select(Category).where(Category.category_id == product_data.category_id)
        category = await db.execute(category_query)
        category = category.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {product_data.category_id} not found"
            )
    
    # Update product attributes
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    
    product.updated_at = datetime.now()
    await db.commit()
    await db.refresh(product)
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-delete a product.
    Requires authentication.
    """
    # Get the product
    query = select(Product).where(
        Product.product_id == product_id,
        Product.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Soft delete the product
    product.deleted_at = datetime.now()
    await db.commit()
    
    return None  # 204 No Content
