from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List

from app.models.plugin import Plugin
from app.models.version import Version
from app.services.transactions import commit_or_rollback


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
        max_app_version: Optional[str] = None,
        plugin: Optional[Plugin] = None
    ) -> Version:
        """创建新版本"""
        async with commit_or_rollback(db):
            new_version = Version(
                plugin_id=plugin_id,
                version=version,
                changelog=changelog,
                download_url=download_url,
                min_app_version=min_app_version,
                max_app_version=max_app_version
            )

            db.add(new_version)
            await db.flush()

            if plugin is not None:
                VersionService._sync_plugin_current_version(plugin, version)

        await db.refresh(new_version)
        return new_version

    @staticmethod
    def _sync_plugin_current_version(plugin: Plugin, version: str) -> None:
        plugin.version = version
    
    @staticmethod
    async def delete_version(db: AsyncSession, version: Version) -> None:
        """删除版本"""
        async with commit_or_rollback(db):
            await db.delete(version)
    
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
