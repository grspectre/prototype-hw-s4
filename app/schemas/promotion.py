from typing import List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator, UUID4, ConfigDict, ValidationInfo

class ProductBasePromotion(BaseModel):
    product_id: UUID4

class ProductInfoPromotion(ProductBasePromotion):
    name: str
    price: float
    rating: float
    
    model_config = ConfigDict(
        from_attributes=True,
    )

# Promotion models
class PromotionBase(BaseModel):
    name: str
    description: str
    url: Optional[str] = None
    start_date: datetime
    end_date: datetime

class PromotionCreate(PromotionBase):
    image_base64: Optional[str] = None
    product_ids: Optional[List[UUID4]] = []
    
    @field_validator('end_date')
    def end_date_after_start_date(cls, v, info: ValidationInfo):
        # Use info.data to access other fields
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_base64: Optional[str] = None
    url: Optional[HttpUrl] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    product_ids: Optional[List[UUID4]] = None
    
    @field_validator('end_date')
    def end_date_after_start_date(cls, v, info):
        start_date = info.data.get('start_date')
        if v is not None and start_date is not None and v < start_date:
            raise ValueError('end_date must be after start_date')
        return v

class PromotionResponse(PromotionBase):
    promotion_id: UUID4
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    products: List[ProductInfoPromotion] = []
    
    model_config = ConfigDict(
        from_attributes=True,
    )

class PromotionListResponse(BaseModel):
    items: List[PromotionResponse]
    total: int

class PromotionProductsUpdate(BaseModel):
    product_ids: List[UUID4]

# Query parameters for filtering promotions
class PromotionFilterParams(BaseModel):
    active_only: Optional[bool] = False
    product_id: Optional[UUID4] = None
    skip: Optional[int] = 0
    limit: Optional[int] = 100

# Error response
class ErrorResponse(BaseModel):
    detail: str
