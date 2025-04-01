# app/routers/reviews.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.db.base import User, Review, Product
from app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.core.security import get_current_user

router = APIRouter()

@router.post("", response_model=ReviewRead)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new review for a product.
    Requires authentication.
    """
    # Check if the product exists
    product_query = select(Product).where(
        Product.product_id == review_data.product_id,
        Product.deleted_at.is_(None)
    )
    result = await db.execute(product_query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {review_data.product_id} not found"
        )
    
    # Check if user already has a review for this product
    existing_review_query = select(Review).where(
        Review.product_id == review_data.product_id,
        Review.user_id == current_user.user_id,
        Review.deleted_at.is_(None)
    )
    result = await db.execute(existing_review_query)
    existing_review = result.scalar_one_or_none()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product"
        )
    
    # Create the review
    review = Review(
        user_id=current_user.user_id,
        product_id=review_data.product_id,
        text=review_data.text,
        rating=review_data.rating,
    )
    
    db.add(review)
    await db.commit()
    await db.refresh(review)
    
    return review

@router.get("", response_model=PaginatedResponse[ReviewRead])
async def list_reviews(
    product_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    List reviews with optional filtering by product, user, or rating range.
    Supports pagination.
    """
    query = select(Review).where(Review.deleted_at.is_(None))
    
    # Apply filters
    if product_id:
        query = query.where(Review.product_id == product_id)
    
    if user_id:
        query = query.where(Review.user_id == user_id)
    
    if min_rating:
        query = query.where(Review.rating >= min_rating)
    
    if max_rating:
        query = query.where(Review.rating <= max_rating)
    
    # Count total matching reviews
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Paginate
    query = query.order_by(Review.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=reviews,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )

@router.get("/product/{product_id}", response_model=PaginatedResponse[ReviewRead])
async def get_product_reviews(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all reviews for a specific product.
    Supports pagination and rating filters.
    """
    # Check if the product exists
    product_query = select(Product).where(
        Product.product_id == product_id,
        Product.deleted_at.is_(None)
    )
    result = await db.execute(product_query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Build review query
    query = select(Review).where(
        Review.product_id == product_id,
        Review.deleted_at.is_(None)
    )
    
    # Apply rating filters
    if min_rating:
        query = query.where(Review.rating >= min_rating)
    
    if max_rating:
        query = query.where(Review.rating <= max_rating)
    
    # Count total matching reviews
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Paginate
    query = query.order_by(Review.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=reviews,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )

@router.get("/my", response_model=PaginatedResponse[ReviewRead])
async def get_user_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all reviews created by the current authenticated user.
    Supports pagination.
    """
    query = select(Review).where(
        Review.user_id == current_user.user_id,
        Review.deleted_at.is_(None)
    )
    
    # Count total reviews
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # Paginate
    query = query.order_by(Review.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    reviews = result.scalars().all()
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=reviews,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/statistics/{product_id}", response_model=dict)
async def get_review_statistics(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get statistics about reviews for a specific product.
    Returns average rating and counts by rating level.
    """
    # Check if the product exists
    product_query = select(Product).where(
        Product.product_id == product_id,
        Product.deleted_at.is_(None)
    )
    result = await db.execute(product_query)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    # Get average rating
    avg_query = select(func.avg(Review.rating)).where(
        Review.product_id == product_id,
        Review.deleted_at.is_(None)
    )
    result = await db.execute(avg_query)
    avg_rating = result.scalar_one_or_none() or 0
    
    # Get total reviews count
    count_query = select(func.count()).where(
        Review.product_id == product_id,
        Review.deleted_at.is_(None)
    )
    result = await db.execute(count_query)
    total_reviews = result.scalar_one()
    
    # Get counts by rating
    rating_counts = {}
    for rating in range(1, 6):
        count_query = select(func.count()).where(
            Review.product_id == product_id,
            Review.rating == rating,
            Review.deleted_at.is_(None)
        )
        result = await db.execute(count_query)
        count = result.scalar_one()
        rating_counts[f"{rating}_star"] = count
    
    return {
        "product_id": product_id,
        "average_rating": round(avg_rating, 1),
        "total_reviews": total_reviews,
        "rating_counts": rating_counts
    }


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific review by its ID.
    """
    query = select(Review).where(
        Review.review_id == review_id,
        Review.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found"
        )
    
    return review

@router.put("/{review_id}", response_model=ReviewRead)
async def update_review(
    review_id: UUID,
    review_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing review.
    Only the original author can update their review.
    """
    query = select(Review).where(
        Review.review_id == review_id,
        Review.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found"
        )
    
    # Check if the current user is the author of the review
    if review.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this review"
        )
    
    # Update review attributes
    update_data = review_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(review, key, value)
    
    review.updated_at = datetime.now()
    await db.commit()
    await db.refresh(review)
    
    return review

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a review.
    Only the original author can delete their review.
    Uses soft delete.
    """
    query = select(Review).where(
        Review.review_id == review_id,
        Review.deleted_at.is_(None)
    )
    
    result = await db.execute(query)
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found"
        )
    
    # Check if the current user is the author of the review
    if review.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this review"
        )
    
    # Soft delete the review
    review.deleted_at = datetime.now()
    await db.commit()
    
    return None
