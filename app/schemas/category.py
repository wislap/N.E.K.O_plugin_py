from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    slug: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    slug: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None


class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    plugin_count: Optional[int] = 0
