"""版本管理 HTTP 路由（重构后）。

仅保留 4 个端点：
- `POST /plugins/{id}/versions/publish-from-release` 作者发版
- `POST /plugins/{id}/versions/{version_id}/yank` 撤回
- `GET /plugins/{id}/versions` 列表（支持 channel / include_yanked）
- `GET /plugins/{id}/versions/latest` 当前最新（仅 is_latest=true & 非 yanked）

旧的 `POST /versions`（手填 sha256）/ `DELETE /versions/{id}` 已删除；
任何对它们的调用 FastAPI 自动返 404 / 405（spec R8）。
"""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.errors.version_errors import VersionDomainError
from app.models.plugin import Plugin
from app.models.user import User
from app.schemas.version import (
    Version as VersionSchema,
    VersionPublishRequest,
    VersionYankRequest,
    VersionYankResponse,
)
from app.services.plugin_service import PluginService
from app.services.version_service import VersionService

router = APIRouter()


async def _ensure_plugin(db: AsyncSession, plugin_id: int) -> Plugin:
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在",
        )
    return plugin


@router.get(
    "/plugins/{plugin_id}/versions",
    response_model=List[VersionSchema],
)
async def list_plugin_versions(
    plugin_id: int,
    channel: Optional[Literal["stable", "beta"]] = Query(
        default=None, description="按渠道过滤；不传返回所有渠道"
    ),
    include_yanked: bool = Query(
        default=False, description="是否包含已撤回版本，默认 false"
    ),
    db: AsyncSession = Depends(get_db),
):
    plugin = await _ensure_plugin(db, plugin_id)
    return await VersionService.list_versions(
        db,
        plugin.id,
        channel=channel,
        include_yanked=include_yanked,
    )



@router.get(
    "/plugins/{plugin_id}/versions/latest",
    response_model=VersionSchema,
)
async def get_latest_plugin_version(
    plugin_id: int,
    channel: Literal["stable", "beta"] = Query(
        default="stable", description="目标渠道，默认 stable"
    ),
    db: AsyncSession = Depends(get_db),
):
    """仅返回 is_latest=true AND yanked_at IS NULL 的那条；找不到 404。

    R0 灵魂条款：返回的 package_url 必然指向真实可下载、字节级 sha256 与
    package_sha256 严格一致的 .neko-plugin / .neko-bundle，永远不会
    fallback 到 repo_url 等其他字段。
    """
    plugin = await _ensure_plugin(db, plugin_id)
    version = await VersionService.get_latest(db, plugin.id, channel=channel)
    if version is None:
        raise VersionDomainError(
            "latest_version_not_found",
            "该插件在此 channel 暂无可用版本",
        )
    return version


@router.post(
    "/plugins/{plugin_id}/versions/publish-from-release",
    response_model=VersionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def publish_version_from_release(
    plugin_id: int,
    body: VersionPublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """作者 / 管理员通过 GitHub release URL 发版。

    详细行为见 `VersionService.publish_from_release` 与 spec R3。"""
    plugin = await _ensure_plugin(db, plugin_id)
    version = await VersionService.publish_from_release(
        db,
        plugin=plugin,
        actor=current_user,
        release_url=body.release_url,
        channel=body.channel,
        changelog=body.changelog,
    )
    return version


@router.post(
    "/plugins/{plugin_id}/versions/{version_id}/yank",
    response_model=VersionYankResponse,
)
async def yank_plugin_version(
    plugin_id: int,
    version_id: int,
    body: VersionYankRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤回单向。如被撤回的是 latest，自动晋级该 channel 的次新非 yanked 版本。"""
    plugin = await _ensure_plugin(db, plugin_id)
    version = await VersionService.get_version_by_id(db, version_id)
    if version is None or version.plugin_id != plugin_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="版本不存在",
        )
    yanked, promoted = await VersionService.yank(
        db,
        plugin=plugin,
        version=version,
        actor=current_user,
        reason=body.reason,
    )
    return VersionYankResponse(yanked=yanked, promoted=promoted)
