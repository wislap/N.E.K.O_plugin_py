from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=200)


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    avatar_url: Optional[str]
    bio: Optional[str]
    website: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    plugin_count: Optional[int] = 0


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
