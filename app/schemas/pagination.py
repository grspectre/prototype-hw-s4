# app/schemas/pagination.py
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
