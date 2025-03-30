from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.base import User, CartItem, Product
from app.schemas.cart import (
    CartItemCreate, 
    CartItemUpdate, 
    CartItemRead,
    CartItemDetailRead
)
from app.schemas.pagination import PaginationParams, PaginatedResponse
from app.core.security import get_current_user

router = APIRouter()


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a product to the user's shopping cart.
    If the product is already in the cart, the quantity will be increased.
    Requires authentication.
    """
    # Check if product exists and is not deleted
    product_query = select(Product).where(
        Product.product_id == item.product_id,
        Product.deleted_at.is_(None)
    )
    result = await db.execute(product_query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {item.product_id} not found"
        )
    
    # Check if product is already in cart
    existing_item_query = select(CartItem).where(
        CartItem.user_id == current_user.user_id,
        CartItem.product_id == item.product_id
    )
    result = await db.execute(existing_item_query)
    existing_item = result.scalar_one_or_none()
    
    if existing_item:
        # Update quantity instead of creating a new entry
        existing_item.quantity += item.quantity
        await db.commit()
        await db.refresh(existing_item)
        return existing_item
    
    # Create new cart item
    cart_item = CartItem(
        user_id=current_user.user_id,
        product_id=item.product_id,
        quantity=item.quantity
    )
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)
    
    return cart_item


@router.get("/items", response_model=PaginatedResponse[CartItemDetailRead])
async def get_cart_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    min_quantity: Optional[int] = Query(None, description="Filter by minimum quantity", gt=0),
    max_quantity: Optional[int] = Query(None, description="Filter by maximum quantity", gt=0),
):
    """
    Get all items in the user's shopping cart with pagination and filtering options.
    Requires authentication.
    """
    # Base query with join to products
    query = select(CartItem).where(
        CartItem.user_id == current_user.user_id
    ).options(selectinload(CartItem.product))
    
    # Apply filters if provided
    if product_id:
        query = query.where(CartItem.product_id == product_id)
    if min_quantity:
        query = query.where(CartItem.quantity >= min_quantity)
    if max_quantity:
        query = query.where(CartItem.quantity <= max_quantity)
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total = await db.scalar(count_query) or 0
    
    # Apply pagination
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
    
    # Execute query
    result = await db.execute(query)
    cart_items = result.scalars().all()
    
    # Calculate pages
    pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return PaginatedResponse(
        items=cart_items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages
    )


@router.get("/items/{cart_item_id}", response_model=CartItemDetailRead)
async def get_cart_item(
    cart_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific cart item by ID.
    Requires authentication.
    """
    query = select(CartItem).where(
        CartItem.cart_item_id == cart_item_id,
        CartItem.user_id == current_user.user_id
    ).options(selectinload(CartItem.product))
    
    result = await db.execute(query)
    cart_item = result.scalar_one_or_none()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with ID {cart_item_id} not found"
        )
    
    return cart_item


@router.put("/items/{cart_item_id}", response_model=CartItemRead)
async def update_cart_item(
    cart_item_id: UUID,
    item_data: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the quantity of a cart item.
    Requires authentication.
    """
    query = select(CartItem).where(
        CartItem.cart_item_id == cart_item_id,
        CartItem.user_id == current_user.user_id
    )
    
    result = await db.execute(query)
    cart_item = result.scalar_one_or_none()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with ID {cart_item_id} not found"
        )
    
    # Update cart item attributes
    update_data = item_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cart_item, key, value)
    
    await db.commit()
    await db.refresh(cart_item)
    
    return cart_item


@router.delete("/items/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    cart_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an item from the shopping cart.
    Requires authentication.
    """
    query = select(CartItem).where(
        CartItem.cart_item_id == cart_item_id,
        CartItem.user_id == current_user.user_id
    )
    
    result = await db.execute(query)
    cart_item = result.scalar_one_or_none()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with ID {cart_item_id} not found"
        )
    
    await db.delete(cart_item)
    await db.commit()
    
    return None


@router.delete("/items", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove all items from the user's shopping cart.
    Requires authentication.
    """
    query = select(CartItem).where(CartItem.user_id == current_user.user_id)
    result = await db.execute(query)
    cart_items = result.scalars().all()
    
    for item in cart_items:
        await db.delete(item)
    
    await db.commit()
    
    return None


@router.get("/count", response_model=int)
async def get_cart_item_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the total number of items in the user's shopping cart.
    Requires authentication.
    """
    query = select(func.sum(CartItem.quantity)).where(
        CartItem.user_id == current_user.user_id
    )
    
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return count
