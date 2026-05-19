"""版本管理 Pydantic schema。

旧的 `VersionCreate`（手填 sha256 的版本创建请求体）已删除；发版统一走
`VersionPublishRequest` → `POST /publish-from-release`，撤回统一走
`VersionYankRequest` → `POST /yank`。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ChannelLiteral = Literal["stable", "beta"]


class VersionPublishRequest(BaseModel):
    """作者通过 GitHub Release URL 发版的请求体。

    后端会拉取 release asset 字节级算 sha256 后写入；作者无法（也不应）
    在请求中提供 sha256 / payload_hash 等 Frozen_Fact 字段。
    """

    release_url: str = Field(..., max_length=500)
    channel: ChannelLiteral = "stable"
    changelog: Optional[str] = None


class VersionReleaseCandidate(BaseModel):
    tag_name: str
    name: Optional[str] = None
    release_url: str
    published_at: Optional[datetime] = None
    draft: bool = False
    prerelease: bool = False
    asset_names: List[str] = []
    has_package_asset: bool = False


class VersionYankRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class Version(BaseModel):
    """对外暴露的 Version 对象。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plugin_id: int
    version: str
    channel: str
    is_latest: bool
    yanked_at: Optional[datetime] = None
    yanked_reason: Optional[str] = None
    yanked_by: Optional[int] = None
    published_by: Optional[int] = None
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    package_url: Optional[str] = None
    package_sha256: Optional[str] = None
    payload_hash: Optional[str] = None
    release_tag: Optional[str] = None
    release_url: Optional[str] = None
    source_commit: Optional[str] = None
    source_repo_url: Optional[str] = None
    actions_run_url: Optional[str] = None
    neko_repo: Optional[str] = None
    neko_ref: Optional[str] = None
    neko_commit: Optional[str] = None
    verification_status: str
    verification_summary: Optional[str] = None
    min_app_version: Optional[str] = None
    max_app_version: Optional[str] = None
    created_at: datetime


class VersionYankResponse(BaseModel):
    yanked: Version
    promoted: Optional[Version] = None
