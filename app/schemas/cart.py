from typing import Optional, List
from pydantic import BaseModel, UUID4, Field, ConfigDict
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

    model_config = ConfigDict(
        from_attributes=True,
    )

class CartItemDetailRead(CartItemRead):
    product: ProductRead

    model_config = ConfigDict(
        from_attributes=True,
    )
