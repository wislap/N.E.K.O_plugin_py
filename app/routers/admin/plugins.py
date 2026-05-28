from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.plugin import PluginStatus
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.plugin import PluginList, PluginSearchParams
from app.services.plugin_projection import attach_latest_version
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/plugins", tags=["admin-plugins"])
require_plugin_management = PermissionChecker("plugin:manage")


@router.get("", response_model=PaginatedResponse[PluginList])
async def list_admin_plugins(
    q: str | None = Query(None, description="搜索关键词"),
    category: str | None = Query(None, description="分类 slug"),
    author: str | None = Query(None, description="作者名"),
    plugin_status: PluginStatus | None = Query(None, alias="status", description="插件状态"),
    sort_by: str | None = Query("created_at", description="排序字段"),
    sort_order: str | None = Query("desc", description="排序方向: asc/desc"),
    featured_only: bool = Query(False, description="仅显示推荐插件"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_plugin_management),
    db: AsyncSession = Depends(get_db),
):
    params = PluginSearchParams(
        q=q,
        category=category,
        author=author,
        sort_by=sort_by,
        sort_order=sort_order,
        status=plugin_status,
        featured_only=featured_only,
    )
    result = await PluginService.get_plugins(
        db,
        params,
        page=page,
        page_size=page_size,
        include_unpublished=True,
    )
    await attach_latest_version(db, result.items)
    return result


@router.delete("/{plugin_id}", response_model=MessageResponse)
async def delete_admin_plugin(
    plugin_id: int,
    current_user: User = Depends(require_plugin_management),
    db: AsyncSession = Depends(get_db),
):
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="插件不存在")

    await PluginService.delete_plugin(db, plugin)
    return MessageResponse(message="插件已删除")
