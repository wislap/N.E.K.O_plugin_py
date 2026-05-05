from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

from app.models.plugin import PluginStatus


class PluginBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=255)
    download_url: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = Field(None, max_length=500)
    repo_url: Optional[str] = Field(None, max_length=500, description="GitHub仓库地址，格式：https://github.com/用户名/n.e.k.o_plugin_xxx")
    readme: Optional[str] = None
    zone_id: Optional[int] = None
    zone_slug: Optional[str] = Field(None, max_length=50)
    tags: List[str] = []


class PluginUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=255)
    download_url: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = Field(None, max_length=500)
    repo_url: Optional[str] = Field(None, max_length=500)
    readme: Optional[str] = None
    zone_id: Optional[int] = None
    zone_slug: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None
    category_ids: Optional[List[int]] = None


class PluginCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class PluginAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]


class Plugin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    short_description: Optional[str]
    author_id: int
    author_name: str
    version: str
    icon_url: Optional[str]
    download_url: Optional[str]
    repo_url: Optional[str]
    readme: Optional[str]
    zone_id: Optional[int]
    zone_slug: Optional[str]
    tags: List[str]
    download_count: int
    likes: int
    rating_average: float
    rating_count: int
    status: PluginStatus
    is_featured: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


class PluginList(Plugin):
    model_config = ConfigDict(from_attributes=True)

    categories: List[PluginCategory] = []


class PluginDetail(PluginList):
    model_config = ConfigDict(from_attributes=True)

    description: Optional[str]
    author: PluginAuthor


class PluginSearchParams(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    sort_by: Optional[str] = Field("created_at", pattern="^(created_at|download_count|rating_average|name)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    status: Optional[PluginStatus] = None
    featured_only: Optional[bool] = False
