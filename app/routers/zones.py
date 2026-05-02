from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.services.zone_service import ZoneService

router = APIRouter()


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
