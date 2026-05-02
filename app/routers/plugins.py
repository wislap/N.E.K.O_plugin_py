from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.schemas.plugin import (
    PluginCreate, PluginUpdate, PluginList, PluginDetail,
    PluginSearchParams, Plugin as PluginSchema
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.plugin_service import PluginService
from app.services.plugin_review_service import PluginReviewService
from app.models.plugin import PluginStatus

router = APIRouter()


class PluginReviewDecisionRequest(BaseModel):
    comment: Optional[str] = None


@router.get("/plugins", response_model=PaginatedResponse[PluginList])
async def list_plugins(
    q: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类slug"),
    author: Optional[str] = Query(None, description="作者名"),
    plugin_status: Optional[PluginStatus] = Query(None, alias="status", description="插件状态"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    featured_only: bool = Query(False, description="仅显示推荐插件"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取公开插件列表，支持搜索和筛选。

    公开列表只允许查看已发布插件；待审核/已拒绝插件走管理员接口。
    """
    if plugin_status and plugin_status != PluginStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能通过管理员接口查看非公开插件"
        )

    params = PluginSearchParams(
        q=q,
        category=category,
        author=author,
        sort_by=sort_by,
        sort_order=sort_order,
        status=plugin_status,
        featured_only=featured_only
    )
    
    result = await PluginService.get_plugins(db, params, page, page_size)
    return result


@router.get("/admin/plugins", response_model=PaginatedResponse[PluginList])
async def list_admin_plugins(
    q: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类slug"),
    author: Optional[str] = Query(None, description="作者名"),
    plugin_status: Optional[PluginStatus] = Query(None, alias="status", description="插件状态"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    featured_only: bool = Query(False, description="仅显示推荐插件"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取管理员插件列表，可查看所有审核状态。
    """
    params = PluginSearchParams(
        q=q,
        category=category,
        author=author,
        sort_by=sort_by,
        sort_order=sort_order,
        status=plugin_status,
        featured_only=featured_only
    )

    return await PluginService.get_plugins(
        db,
        params,
        page,
        page_size,
        include_unpublished=True
    )


@router.get("/plugins/featured", response_model=List[PluginList])
async def get_featured_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    获取推荐插件列表
    """
    plugins = await PluginService.get_featured_plugins(db, limit)
    return plugins


@router.get("/plugins/popular", response_model=List[PluginList])
async def get_popular_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    获取热门插件列表（按下载量排序）
    """
    plugins = await PluginService.get_popular_plugins(db, limit)
    return plugins


@router.get("/plugins/newest", response_model=List[PluginList])
async def get_newest_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    获取最新插件列表
    """
    plugins = await PluginService.get_newest_plugins(db, limit)
    return plugins


@router.get("/plugins/mine", response_model=List[PluginList])
async def get_my_plugins(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户提交的插件列表
    """
    plugins = await PluginService.get_plugins_by_author(db, current_user.id)
    return plugins


@router.get("/plugins/{plugin_id}", response_model=PluginDetail)
async def get_plugin(
    plugin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件详情
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin or plugin.status != PluginStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在或尚未发布"
        )
    return plugin


@router.get("/plugins/slug/{slug}", response_model=PluginDetail)
async def get_plugin_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    通过slug获取插件详情
    """
    plugin = await PluginService.get_plugin_by_slug(db, slug)
    if not plugin or plugin.status != PluginStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在或尚未发布"
        )
    return plugin


@router.post("/plugins", response_model=PluginSchema, status_code=status.HTTP_201_CREATED)
async def create_plugin(
    plugin_data: PluginCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新插件（需要登录）
    """
    try:
        plugin = await PluginService.create_plugin(
            db, plugin_data, 
            author_id=current_user.id, 
            author_name=current_user.username
        )
        return plugin
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/plugins/{plugin_id}", response_model=PluginSchema)
async def update_plugin(
    plugin_id: int,
    update_data: PluginUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新插件信息（需要插件所有者或管理员权限）
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    # 检查权限
    if plugin.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此插件"
        )
    
    updated_plugin = await PluginService.update_plugin(db, plugin, update_data)
    return updated_plugin


@router.delete("/plugins/{plugin_id}", response_model=MessageResponse)
async def delete_plugin(
    plugin_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除插件（需要插件所有者或管理员权限）
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    # 检查权限
    if plugin.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此插件"
        )
    
    await PluginService.delete_plugin(db, plugin)
    return MessageResponse(message="插件已删除")


@router.post("/plugins/{plugin_id}/approve", response_model=PluginSchema)
async def approve_plugin(
    plugin_id: int,
    decision: Optional[PluginReviewDecisionRequest] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    审核通过插件（需要管理员权限）
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    review_service = PluginReviewService()
    approved_plugin = await review_service.record_admin_decision(
        db,
        plugin,
        "approve",
        current_user.id,
        (decision.comment if decision else None) or "",
    )
    return approved_plugin


@router.post("/plugins/{plugin_id}/reject", response_model=PluginSchema)
async def reject_plugin(
    plugin_id: int,
    decision: Optional[PluginReviewDecisionRequest] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    拒绝插件（需要管理员权限）
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    review_service = PluginReviewService()
    rejected_plugin = await review_service.record_admin_decision(
        db,
        plugin,
        "reject",
        current_user.id,
        (decision.comment if decision else None) or "",
    )
    return rejected_plugin


@router.post("/plugins/{plugin_id}/download", response_model=MessageResponse)
async def record_download(
    plugin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    记录插件下载
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin or plugin.status != PluginStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在或尚未发布"
        )
    
    await PluginService.increment_download_count(db, plugin_id)
    return MessageResponse(message="下载记录已更新")
