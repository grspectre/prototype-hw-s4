import uuid
import base64
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pathlib import Path as FilePath
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.base import (
    User, 
    Product, 
    Promotion, 
    get_promotion_by_id, 
    get_active_promotions, 
    get_promotions_for_product,
)
from app.schemas.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    PromotionListResponse,
    PromotionProductsUpdate,
    PromotionFilterParams,
    ErrorResponse
)
from app.core.security import get_current_user

router = APIRouter()


# Helper function to save base64 image
async def save_promotion_image(image_base64: str, promotion_id: uuid.UUID) -> tuple[str, str]:
    """
    Save base64 encoded image and return file path and URL
    """
    if not image_base64:
        return None, None
    
    # Create directory if not exists
    upload_dir = FilePath("static/images/promotions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Decode the base64 string
    image_data = base64.b64decode(image_base64)
    
    # Generate filename
    filename = f"{promotion_id}.jpg"
    file_path = upload_dir / filename
    
    # Write image to file
    with open(file_path, "wb") as f:
        f.write(image_data)
    
    # Return file path and URL
    image_path = str(file_path)
    image_url = f"/static/images/promotions/{filename}"
    
    return image_path, image_url


@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    }
)
async def create_promotion(
    promotion: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new promotional campaign.
    Only available to admin users.
    """
    # Create new promotion
    new_promotion = Promotion(
        name=promotion.name,
        description=promotion.description,
        url=promotion.url,
        start_date=promotion.start_date,
        end_date=promotion.end_date,
    )
    
    # Save image if provided
    if promotion.image_base64:
        image_path, image_url = await save_promotion_image(
            promotion.image_base64, 
            new_promotion.promotion_id
        )
        new_promotion.image_path = image_path
        new_promotion.image_url = image_url
    
    # Add products if provided
    if promotion.product_ids:
        for product_id in promotion.product_ids:
            product = await db.get(Product, product_id)
            if product:
                new_promotion.products.append(product)
    
    # Save to database
    db.add(new_promotion)
    await db.commit()

    stmt = select(Promotion).options(
        selectinload(Promotion.products)
    ).where(Promotion.promotion_id == new_promotion.promotion_id)
    
    result = await db.execute(stmt)
    loaded_promotion = result.scalar_one()
    
    return loaded_promotion


@router.get(
    "",
    response_model=PromotionListResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    }
)
async def list_promotions(
    filter_params: PromotionFilterParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List all promotional campaigns with filtering options.
    Can filter by active status or by associated product.
    """
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload  # Add this import
    
    # Base query with eager loading of products
    query = select(Promotion).options(selectinload(Promotion.products)).where(Promotion.deleted_at.is_(None))
    count_query = select(func.count()).select_from(Promotion).where(Promotion.deleted_at.is_(None))
    
    # Apply filters
    if filter_params.active_only:
        now = datetime.now()
        condition = (Promotion.start_date <= now) & (Promotion.end_date >= now)
        query = query.where(condition)
        count_query = count_query.where(condition)
    
    if filter_params.product_id:
        from sqlalchemy import and_
        from app.db.base import promotion_product
        
        query = query.join(
            promotion_product, 
            promotion_product.c.promotion_id == Promotion.promotion_id
        ).where(promotion_product.c.product_id == filter_params.product_id)
        
        count_query = count_query.join(
            promotion_product, 
            promotion_product.c.promotion_id == Promotion.promotion_id
        ).where(promotion_product.c.product_id == filter_params.product_id)
    
    # Pagination
    total = await db.execute(count_query)
    total_count = total.scalar() or 0
    
    query = query.offset(filter_params.skip).limit(filter_params.limit)
    
    # Execute query
    result = await db.execute(query)
    promotions = result.scalars().all()
    
    return PromotionListResponse(
        items=list(promotions),
        total=total_count
    )


@router.get(
    "/active",
    response_model=List[PromotionResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    }
)
async def get_active_promotions_list(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all currently active promotional campaigns.
    """
    current_date = datetime.now()
    active_promotions = await get_active_promotions(db, current_date)
    return active_promotions


@router.get(
    "/product/{product_id}",
    response_model=List[PromotionResponse],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    }
)
async def get_promotions_by_product(
    product_id: uuid.UUID = Path(..., title="The ID of the product"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all promotional campaigns associated with a specific product.
    """
    # First check if the product exists
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    promotions = await get_promotions_for_product(db, product_id)
    return promotions


@router.get(
    "/{promotion_id}",
    response_model=PromotionResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    }
)
async def get_promotion(
    promotion_id: uuid.UUID = Path(..., title="The ID of the promotion to get"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific promotional campaign by ID.
    """
    promotion = await get_promotion_by_id(db, promotion_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )
    
    return promotion

@router.put(
    "/{promotion_id}",
    response_model=PromotionResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    }
)
async def update_promotion(
    promotion_id: uuid.UUID = Path(..., title="The ID of the promotion to update"),
    promotion_update: PromotionUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing promotional campaign.
    Only available to admin users.
    """
    promotion = await get_promotion_by_id(db, promotion_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )
    
    # Update basic fields
    if promotion_update.name is not None:
        promotion.name = promotion_update.name
    
    if promotion_update.description is not None:
        promotion.description = promotion_update.description
    
    if promotion_update.url is not None:
        promotion.url = str(promotion_update.url)
    
    if promotion_update.start_date is not None:
        promotion.start_date = promotion_update.start_date
    
    if promotion_update.end_date is not None:
        promotion.end_date = promotion_update.end_date
    
    # Update image if provided
    if promotion_update.image_base64:
        image_path, image_url = await save_promotion_image(
            promotion_update.image_base64,
            promotion.promotion_id
        )
        promotion.image_path = image_path
        promotion.image_url = image_url
    
    # Update products if provided
    if promotion_update.product_ids is not None:
        # Clear existing products
        promotion.products = []
        
        for product_id in promotion_update.product_ids:
            product = await db.get(Product, product_id)
            if product:
                promotion.products.append(product)
    
    # Save changes
    promotion.updated_at = datetime.now()
    await db.commit()

    stmt = select(Promotion).options(
        selectinload(Promotion.products)
    ).where(Promotion.promotion_id == promotion.promotion_id)
    
    result = await db.execute(stmt)
    promotion = result.scalar_one()
    
    return promotion


@router.delete(
    "/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    }
)
async def delete_promotion(
    promotion_id: uuid.UUID = Path(..., title="The ID of the promotion to delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a promotional campaign.
    Only available to admin users.
    """
    promotion = await get_promotion_by_id(db, promotion_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )
    
    # Soft delete
    promotion.deleted_at = datetime.now()
    await db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{promotion_id}/products",
    response_model=PromotionResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    }
)
async def update_promotion_products(
    promotion_id: uuid.UUID = Path(..., title="The ID of the promotion"),
    product_update: PromotionProductsUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the list of products associated with a promotion.
    Only available to admin users.
    """
    promotion = await get_promotion_by_id(db, promotion_id)
    
    if not promotion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Promotion with ID {promotion_id} not found"
        )
    
    # Replace existing products
    promotion.products = []
    
    for product_id in product_update.product_ids:
        product = await db.get(Product, product_id)
        if product:
            promotion.products.append(product)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {product_id} not found"
            )
    
    # Save changes
    promotion.updated_at = datetime.now()
    await db.commit()

    stmt = select(Promotion).options(
        selectinload(Promotion.products)
    ).where(Promotion.promotion_id == promotion.promotion_id)
    
    result = await db.execute(stmt)
    promotion = result.scalar_one()
    
    return promotion
