from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class ReviewBase(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
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
