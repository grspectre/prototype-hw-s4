from typing import Optional
from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class ReviewBase(BaseModel):
    product_id: UUID4
    text: str
    rating: int = Field(..., ge=1, le=5)

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)

class ReviewRead(ReviewBase):
    review_id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
