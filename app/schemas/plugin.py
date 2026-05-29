from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

from app.models.plugin import PluginStatus


class LatestVersionPublic(BaseModel):
    """挂在 Plugin 对象上的"当前最新版"投影子对象。

    仅包含客户端 / 前端展示所需的最小字段；完整 Version 对象走
    `/plugins/{id}/versions` / `/plugins/{id}/versions/latest` 路由。

    `latest_version is None` 表示该插件在 stable channel 暂无可下载版本
    （首次发布前 / 全部 yanked / 仅 beta 版本）。
    """

    model_config = ConfigDict(from_attributes=True)

    version: str
    channel: str
    package_url: str
    package_sha256: str
    payload_hash: Optional[str] = None
    created_at: datetime


class PluginBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=255)
    icon_url: Optional[str] = Field(None, max_length=500)
    repo_url: Optional[str] = Field(
        None,
        max_length=500,
        description="GitHub仓库地址，格式：https://github.com/用户名/n.e.k.o_plugin_xxx",
    )
    readme: Optional[str] = None
    zone_id: Optional[int] = None
    zone_slug: Optional[str] = Field(None, max_length=50)
    tags: List[str] = []


class PluginUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=255)
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


class RatingSummary(BaseModel):
    functionality: str
    security: str
    documentation: str
    ratedAt: Optional[str] = None


class Plugin(BaseModel):
    """对外暴露的 Plugin 对象。

    重构要点 (market-version-management spec)：
    - 移除顶层 `version` / `download_url`；
    - 新增 `latest_version` 子对象，由 `attach_latest_version` 在响应序列化前
      挂到 Plugin 实例的 `__dict__` 上，Pydantic 走 `from_attributes=True` 读出。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    short_description: Optional[str]
    author_id: int
    author_name: str
    icon_url: Optional[str]
    repo_url: Optional[str]
    readme: Optional[str]
    zone_id: Optional[int]
    zone_slug: Optional[str]
    tags: List[str]
    download_count: int
    likes: int
    liked_by_current_user: bool = False
    rating_average: float
    rating_count: int
    status: PluginStatus
    is_featured: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    latest_version: Optional[LatestVersionPublic] = None
    ai_rating: Optional[RatingSummary] = None
    admin_rating: Optional[RatingSummary] = None


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
    sort_by: Optional[str] = Field(
        "created_at",
        pattern="^(created_at|download_count|likes|name)$",
    )
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    status: Optional[PluginStatus] = None
    featured_only: Optional[bool] = False


class PluginLikeState(BaseModel):
    plugin_id: int
    liked: bool
    likes: int
