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
        source_repo_url: Optional[str] = None,
        source_commit: Optional[str] = None,
        release_tag: Optional[str] = None,
        release_url: Optional[str] = None,
        actions_run_url: Optional[str] = None,
        package_url: Optional[str] = None,
        package_sha256: Optional[str] = None,
        payload_hash: Optional[str] = None,
        neko_repo: Optional[str] = None,
        neko_ref: Optional[str] = None,
        neko_commit: Optional[str] = None,
        verification_status: str = "unverified",
        verification_summary: Optional[str] = None,
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
                max_app_version=max_app_version,
                source_repo_url=source_repo_url,
                source_commit=source_commit,
                release_tag=release_tag,
                release_url=release_url,
                actions_run_url=actions_run_url,
                package_url=package_url,
                package_sha256=package_sha256.lower() if package_sha256 else None,
                payload_hash=payload_hash.lower() if payload_hash else None,
                neko_repo=neko_repo,
                neko_ref=neko_ref,
                neko_commit=neko_commit,
                verification_status=verification_status,
                verification_summary=verification_summary,
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
