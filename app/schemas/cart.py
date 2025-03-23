from typing import Optional, List
from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from .product import ProductRead

class CartItemBase(BaseModel):
    product_id: UUID4
    quantity: int = Field(..., gt=0)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)

class CartItemRead(CartItemBase):
    cart_item_id: UUID4
    user_id: UUID4

    class Config:
        from_attributes = True

class CartItemDetailRead(CartItemRead):
    product: ProductRead

    class Config:
        from_attributes = True
