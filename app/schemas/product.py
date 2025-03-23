# app/schemas/product.py
from typing import Optional, List
from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None

class CategoryRead(CategoryBase):
    category_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    price: float
    category_id: UUID4

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[UUID4] = None

class ProductRead(ProductBase):
    product_id: UUID4
    rating: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProductDetailRead(ProductRead):
    category: CategoryRead
    
    class Config:
        from_attributes = True
