from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime


class ReviewBase(BaseModel):
    rating: float = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None


class ReviewCreate(ReviewBase):
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('评分必须在 1-5 之间')
        return round(v * 2) / 2  # 四舍五入到 0.5


class ReviewUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None


class ReviewAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]


class Review(ReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plugin_id: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[ReviewAuthor] = None
