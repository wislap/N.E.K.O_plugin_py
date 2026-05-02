from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.services.zone_service import ZoneService
from app.models.user import User
from app.schemas.common import MessageResponse

router = APIRouter()
require_zone_management = PermissionChecker("plugin:zone")


@router.get("/zones", response_model=List[dict])
async def list_zones(
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有区域/分区列表（公开API）
    
    返回前端需要的格式，包含插件数量
    """
    zones = await ZoneService.get_zones_with_count(db)
    return zones


@router.get("/zones/{slug}", response_model=dict)
async def get_zone(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取区域详情（公开API）
    """
    zone = await ZoneService.get_zone_by_slug(db, slug)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="区域不存在"
        )
    
    # 获取插件数量
    from sqlalchemy import func, select
    from app.models.plugin import Plugin, PluginStatus
    
    result = await db.execute(
        select(func.count(Plugin.id)).where(
            (Plugin.zone_id == zone.id) &
            (Plugin.status == PluginStatus.APPROVED)
        )
    )
    plugin_count = result.scalar()
    
    return {
        "id": zone.slug,
        "name": zone.name,
        "description": zone.description,
        "icon": zone.icon,
        "color": zone.color,
        "pluginCount": plugin_count
    }


@router.get("/zones/{slug}/plugins", response_model=List[dict])
async def get_zone_plugins(
    slug: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定区域的插件列表（公开API）
    """
    plugins = await ZoneService.get_plugins_by_zone(db, slug, limit)
    return [p.to_frontend_dict() for p in plugins]


@router.get("/admin/zones", response_model=List[dict])
async def list_admin_zones(
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db)
):
    """
    获取后台分区列表，包含数据库 ID 供编辑和删除使用。
    """
    zones = await ZoneService.get_zones(db)
    return [
        {
            "id": zone.id,
            "name": zone.name,
            "slug": zone.slug,
            "description": zone.description,
            "icon": zone.icon,
            "color": zone.color,
            "sort_order": zone.sort_order,
            "created_at": zone.created_at,
            "updated_at": zone.updated_at,
        }
        for zone in zones
    ]


@router.post("/admin/zones", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_zone(
    name: str,
    slug: str,
    description: str = None,
    icon: str = None,
    color: str = None,
    sort_order: int = 0,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新区域（管理员）
    """
    try:
        zone = await ZoneService.create_zone(
            db, name, slug, description, icon, color, sort_order
        )
        return {
            "id": zone.id,
            "name": zone.name,
            "slug": zone.slug,
            "description": zone.description,
            "icon": zone.icon,
            "color": zone.color,
            "sort_order": zone.sort_order,
            "message": "区域创建成功"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/admin/zones/{zone_id}", response_model=dict)
async def update_zone(
    zone_id: int,
    name: str = None,
    description: str = None,
    icon: str = None,
    color: str = None,
    sort_order: int = None,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db)
):
    """
    更新区域信息（管理员）
    """
    zone = await ZoneService.get_zone_by_id(db, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="区域不存在"
        )
    
    updated_zone = await ZoneService.update_zone(
        db, zone, name, description, icon, color, sort_order
    )
    return {
        "id": updated_zone.id,
        "name": updated_zone.name,
        "slug": updated_zone.slug,
        "message": "区域更新成功"
    }


@router.delete("/admin/zones/{zone_id}", response_model=MessageResponse)
async def delete_zone(
    zone_id: int,
    current_user: User = Depends(require_zone_management),
    db: AsyncSession = Depends(get_db)
):
    """
    删除区域（管理员）
    """
    zone = await ZoneService.get_zone_by_id(db, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="区域不存在"
        )
    
    await ZoneService.delete_zone(db, zone)
    return MessageResponse(message="区域已删除")
