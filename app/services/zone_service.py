from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List

from app.models.zone import Zone
from app.models.plugin import Plugin, PluginStatus


class ZoneService:
    """区域/分区服务"""
    
    @staticmethod
    async def get_zone_by_id(db: AsyncSession, zone_id: int) -> Optional[Zone]:
        """通过ID获取区域"""
        result = await db.execute(
            select(Zone).where(Zone.id == zone_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_zone_by_slug(db: AsyncSession, slug: str) -> Optional[Zone]:
        """通过slug获取区域"""
        result = await db.execute(
            select(Zone).where(Zone.slug == slug)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_zones(db: AsyncSession) -> List[Zone]:
        """获取所有区域"""
        result = await db.execute(
            select(Zone).order_by(Zone.sort_order, Zone.name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_zones_with_count(db: AsyncSession) -> List[dict]:
        """获取所有区域及其插件数量"""
        result = await db.execute(
            select(
                Zone,
                func.count(Plugin.id).label('plugin_count')
            )
            .outerjoin(Plugin, (Zone.id == Plugin.zone_id) & (Plugin.status == PluginStatus.APPROVED))
            .group_by(Zone.id)
            .order_by(Zone.sort_order, Zone.name)
        )
        
        zones = []
        for zone, count in result.all():
            zones.append({
                "id": zone.slug,  # 前端使用 slug 作为 id
                "name": zone.name,
                "description": zone.description,
                "icon": zone.icon,
                "color": zone.color,
                "pluginCount": count
            })
        
        return zones
    
    @staticmethod
    async def create_zone(
        db: AsyncSession,
        name: str,
        slug: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: int = 0
    ) -> Zone:
        """创建新区域"""
        # 检查slug是否已存在
        existing = await ZoneService.get_zone_by_slug(db, slug)
        if existing:
            raise ValueError(f"区域slug '{slug}' 已存在")
        
        zone = Zone(
            name=name,
            slug=slug,
            description=description,
            icon=icon,
            color=color,
            sort_order=sort_order
        )
        
        db.add(zone)
        await db.commit()
        await db.refresh(zone)
        return zone
    
    @staticmethod
    async def update_zone(
        db: AsyncSession,
        zone: Zone,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Zone:
        """更新区域"""
        if name is not None:
            zone.name = name
        if description is not None:
            zone.description = description
        if icon is not None:
            zone.icon = icon
        if color is not None:
            zone.color = color
        if sort_order is not None:
            zone.sort_order = sort_order
        
        await db.commit()
        await db.refresh(zone)
        return zone
    
    @staticmethod
    async def delete_zone(db: AsyncSession, zone: Zone) -> None:
        """删除区域"""
        await db.delete(zone)
        await db.commit()
    
    @staticmethod
    async def get_plugins_by_zone(
        db: AsyncSession,
        zone_slug: str,
        limit: Optional[int] = None
    ) -> List[Plugin]:
        """获取指定区域的插件"""
        zone = await ZoneService.get_zone_by_slug(db, zone_slug)
        if not zone:
            return []
        
        query = select(Plugin).where(
            (Plugin.zone_id == zone.id) &
            (Plugin.status == PluginStatus.APPROVED)
        ).order_by(desc(Plugin.download_count))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
