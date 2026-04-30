from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List

from app.models.version import Version


class VersionService:
    
    @staticmethod
    async def get_version_by_id(db: AsyncSession, version_id: int) -> Optional[Version]:
        """通过ID获取版本"""
        result = await db.execute(
            select(Version).where(Version.id == version_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_plugin_versions(
        db: AsyncSession,
        plugin_id: int,
        limit: Optional[int] = None
    ) -> List[Version]:
        """获取插件的所有版本"""
        query = select(Version).where(
            Version.plugin_id == plugin_id
        ).order_by(desc(Version.created_at))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_latest_version(
        db: AsyncSession,
        plugin_id: int
    ) -> Optional[Version]:
        """获取插件的最新版本"""
        result = await db.execute(
            select(Version).where(
                Version.plugin_id == plugin_id
            ).order_by(desc(Version.created_at)).limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_version(
        db: AsyncSession,
        plugin_id: int,
        version: str,
        changelog: Optional[str] = None,
        download_url: Optional[str] = None,
        min_app_version: Optional[str] = None,
        max_app_version: Optional[str] = None
    ) -> Version:
        """创建新版本"""
        new_version = Version(
            plugin_id=plugin_id,
            version=version,
            changelog=changelog,
            download_url=download_url,
            min_app_version=min_app_version,
            max_app_version=max_app_version
        )
        
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)
        return new_version
    
    @staticmethod
    async def delete_version(db: AsyncSession, version: Version) -> None:
        """删除版本"""
        await db.delete(version)
        await db.commit()
    
    @staticmethod
    async def version_exists(
        db: AsyncSession,
        plugin_id: int,
        version: str
    ) -> bool:
        """检查版本是否已存在"""
        result = await db.execute(
            select(Version).where(
                Version.plugin_id == plugin_id,
                Version.version == version
            )
        )
        return result.scalar_one_or_none() is not None
