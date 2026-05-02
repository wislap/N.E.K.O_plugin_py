from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.plugin import PluginStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plugin import Plugin as PluginSchema
from app.schemas.plugin import PluginList, PluginSearchParams
from app.services.plugin_review_service import PluginReviewService
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/plugins", tags=["admin-plugins"])
require_plugin_review = PermissionChecker("plugin:review")


class PluginReviewDecisionRequest(BaseModel):
    comment: Optional[str] = None


@router.get("", response_model=PaginatedResponse[PluginList])
async def list_admin_plugins(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    plugin_status: Optional[PluginStatus] = Query(None, alias="status"),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    featured_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_plugin_review),
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
    return await PluginService.get_plugins(
        db,
        params,
        page,
        page_size,
        include_unpublished=True,
    )


@router.post("/{plugin_id}/approve", response_model=PluginSchema)
async def approve_plugin(
    plugin_id: int,
    decision: Optional[PluginReviewDecisionRequest] = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="插件不存在")

    review_service = PluginReviewService()
    return await review_service.record_admin_decision(
        db,
        plugin,
        "approve",
        current_user.id,
        (decision.comment if decision else None) or "",
    )


@router.post("/{plugin_id}/reject", response_model=PluginSchema)
async def reject_plugin(
    plugin_id: int,
    decision: Optional[PluginReviewDecisionRequest] = None,
    current_user: User = Depends(require_plugin_review),
    db: AsyncSession = Depends(get_db),
):
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="插件不存在")

    review_service = PluginReviewService()
    return await review_service.record_admin_decision(
        db,
        plugin,
        "reject",
        current_user.id,
        (decision.comment if decision else None) or "",
    )
