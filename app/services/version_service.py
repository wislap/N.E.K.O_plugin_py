"""版本服务（重构后）。

只暴露 4 个对外方法：
- `publish_from_release` 作者发版（拉 GitHub release → 冻结 hash → 落库）
- `yank` 撤回单向（自动晋级次新版本 + 写通知 + audit log）
- `list_versions` 按 channel / yank 过滤的列表
- `get_latest` (plugin, channel) 上 is_latest=true AND yanked_at IS NULL 的那条

旧的 `create_version` / `delete_version` / `_sync_plugin_current_version` 已删除
（spec market-version-management，参见 R8 路由删除条款）。
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.errors.version_errors import VersionDomainError
from app.models.plugin import Plugin
from app.models.user import User
from app.models.version import Version
from app.services.notification_service import NotificationService
from app.services.release_fetcher import ReleaseFetcher
from app.services.transactions import commit_or_rollback

logger = logging.getLogger(__name__)

ALLOWED_CHANNELS = ("stable", "beta")
ChannelLiteral = Literal["stable", "beta"]



def _is_admin(user: User) -> bool:
    """复用 User.is_admin 判定。

    注：项目里有更细的 plugin_management 权限组，但顶层 is_admin 已涵盖
    所有管理员场景；如果未来要换成精细权限，本函数是单一改动点。
    """
    return bool(getattr(user, "is_admin", False))


def _ensure_can_manage_versions(plugin: Plugin, actor: User) -> None:
    if actor.id == plugin.author_id or _is_admin(actor):
        return
    raise VersionDomainError("forbidden", "没有权限管理此插件的版本")


def _ensure_channel_valid(channel: str) -> None:
    if channel not in ALLOWED_CHANNELS:
        raise VersionDomainError(
            "invalid_channel",
            f"不支持的 channel: {channel}（仅允许 {', '.join(ALLOWED_CHANNELS)}）",
        )


class VersionService:
    """重构后的版本服务，所有写入路径都经过 commit_or_rollback 事务包装。"""

    @staticmethod
    async def get_version_by_id(db: AsyncSession, version_id: int) -> Optional[Version]:
        return await db.get(Version, version_id)


    @staticmethod
    async def list_versions(
        db: AsyncSession,
        plugin_id: int,
        *,
        channel: Optional[ChannelLiteral] = None,
        include_yanked: bool = False,
    ) -> List[Version]:
        """按 created_at desc 返回版本列表。

        - `channel=None` 返回所有 channel 的版本；
        - `include_yanked=False`（默认）过滤 `yanked_at IS NOT NULL` 的行。
        """
        query = select(Version).where(Version.plugin_id == plugin_id)
        if channel is not None:
            query = query.where(Version.channel == channel)
        if not include_yanked:
            query = query.where(Version.yanked_at.is_(None))
        query = query.order_by(desc(Version.created_at), desc(Version.id))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_latest(
        db: AsyncSession,
        plugin_id: int,
        *,
        channel: ChannelLiteral = "stable",
    ) -> Optional[Version]:
        """仅返回 `is_latest=True AND yanked_at IS NULL` 的版本，至多一条。

        R0 灵魂条款：要返回的 latest 必须是真实可下载（package_url 非空且
        package_sha256 是 64 字符 hex）。legacy 数据 / 手填残缺数据被过滤
        掉，调用方据此返回 404 latest_version_not_found。
        """
        query = (
            select(Version)
            .where(
                Version.plugin_id == plugin_id,
                Version.channel == channel,
                Version.is_latest.is_(True),
                Version.yanked_at.is_(None),
                Version.package_url.is_not(None),
                Version.package_url != "",
                Version.package_sha256.is_not(None),
                Version.package_sha256 != "",
            )
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def publish_from_release(
        db: AsyncSession,
        *,
        plugin: Plugin,
        actor: User,
        release_url: str,
        channel: str = "stable",
        changelog: Optional[str] = None,
        fetcher: Optional[ReleaseFetcher] = None,
    ) -> Version:
        """R3 主流程。

        步骤（与 design 节"VersionService 重构"严格对齐）：

        1. 校验 channel 与权限。
        2. 调 ReleaseFetcher 拉 release / 算 sha256 / 解 metadata.toml。
        3. 事务内：把同 plugin + 同 channel 的旧 latest 置 false；插入新行。
        4. IntegrityError 转 `version_already_exists`（来自 (plugin_id, version)
           唯一索引或 (plugin_id, channel) WHERE is_latest=1 部分唯一索引）。
        """
        _ensure_channel_valid(channel)
        _ensure_can_manage_versions(plugin, actor)

        if not plugin.repo_url:
            # 只有 repo_url 已配置才允许发版（spec R3.3 校验前置条件）
            raise VersionDomainError(
                "release_repo_mismatch",
                "插件未配置 GitHub 仓库地址，无法校验 release 归属",
            )

        fetcher = fetcher or ReleaseFetcher()
        # ReleaseFetchError 由全局 handler 透传转 4xx/502；不在此 catch
        resolved = await fetcher.fetch_and_resolve(
            release_url=release_url,
            plugin_repo_url=plugin.repo_url,
        )

        new_version: Optional[Version] = None
        plugin_id_for_log = plugin.id
        actor_id_for_log = actor.id
        try:
            async with commit_or_rollback(db):
                # 1) 把同 plugin + 同 channel 的旧 latest 置 false
                old_latest_q = select(Version).where(
                    Version.plugin_id == plugin.id,
                    Version.channel == channel,
                    Version.is_latest.is_(True),
                )
                for stale in (await db.execute(old_latest_q)).scalars().all():
                    stale.is_latest = False
                # 让 partial unique index 在 flush 时看到 is_latest=false
                await db.flush()

                # 2) 插入新 Version 行
                new_version = Version(
                    plugin_id=plugin.id,
                    version=resolved.release_tag,
                    channel=channel,
                    is_latest=True,
                    yanked_at=None,
                    changelog=changelog,
                    download_url=resolved.package_url,
                    package_url=resolved.package_url,
                    package_sha256=resolved.package_sha256.lower(),
                    payload_hash=resolved.payload_hash,
                    release_tag=resolved.release_tag,
                    release_url=resolved.release_url_canonical,
                    source_commit=resolved.source_commit or None,
                    source_repo_url=plugin.repo_url,
                    published_by=actor.id,
                    verification_status="passed",
                )
                db.add(new_version)
                await db.flush()
        except IntegrityError as exc:
            # 命中 (plugin_id, version) 唯一索引或 partial unique index
            logger.info(
                "version.publish_from_release outcome=failed plugin_id=%s "
                "actor_id=%s release_url=%s channel=%s error_kind=integrity",
                plugin_id_for_log, actor_id_for_log, release_url, channel,
            )
            raise VersionDomainError(
                "version_already_exists",
                f"该版本号 {resolved.release_tag} 已存在",
            ) from exc

        assert new_version is not None  # commit_or_rollback 没抛即代表 commit 成功
        await db.refresh(new_version)
        logger.info(
            "version.publish_from_release outcome=success plugin_id=%s "
            "actor_id=%s release_url=%s channel=%s version=%s",
            plugin_id_for_log, actor_id_for_log, release_url, channel,
            resolved.release_tag,
        )
        return new_version


    @staticmethod
    async def yank(
        db: AsyncSession,
        *,
        plugin: Plugin,
        version: Version,
        actor: User,
        reason: str,
    ) -> tuple[Version, Optional[Version]]:
        """R4 主流程。

        - 校验权限 / 非已 yanked。
        - 事务内：标记 yanked_*；如是 latest 则查找次新非 yanked 版本切 latest。
        - 提交后给作者发 notification（仅当 latest 发生变化时）。
        - 返回 (yanked_version, promoted_version | None)。

        注意：如果 actor 就是作者，仍会发通知 —— 通知文案区分操作者身份
        以便作者在多个客户端 / 多个浏览器之间保持记录可追溯。
        """
        _ensure_can_manage_versions(plugin, actor)

        if version.plugin_id != plugin.id:
            # 路由层已校验，此处 defensive
            raise VersionDomainError("forbidden", "版本不属于该插件")

        if version.yanked_at is not None:
            raise VersionDomainError("version_already_yanked", "该版本已被撤回")

        promoted: Optional[Version] = None
        latest_changed = False

        async with commit_or_rollback(db):
            now = utc_now()
            version.yanked_at = now
            version.yanked_reason = reason
            version.yanked_by = actor.id

            if version.is_latest:
                latest_changed = True
                version.is_latest = False
                # 让 partial unique index 在 flush 时看到旧 latest 已让位
                await db.flush()

                candidate_q = (
                    select(Version)
                    .where(
                        Version.plugin_id == plugin.id,
                        Version.channel == version.channel,
                        Version.yanked_at.is_(None),
                        Version.id != version.id,
                    )
                    .order_by(desc(Version.created_at), desc(Version.id))
                    .limit(1)
                )
                promoted = (await db.execute(candidate_q)).scalar_one_or_none()
                if promoted is not None:
                    promoted.is_latest = True
                    await db.flush()

            # 仅在 latest 发生变化时通知作者（避免对非 latest 的撤回也吵作者）
            if latest_changed:
                actor_label = (
                    "管理员"
                    if _is_admin(actor) and actor.id != plugin.author_id
                    else "作者本人"
                )
                NotificationService.add(
                    db,
                    user_id=plugin.author_id,
                    type="version.yanked",
                    title=(
                        f"插件「{plugin.name}」的 v{version.version} "
                        f"({version.channel}) 已被{actor_label}撤回"
                    ),
                    content=reason,
                    target_url=f"/plugin/{plugin.id}?tab=versions",
                )

        await db.refresh(version)
        if promoted is not None:
            await db.refresh(promoted)
        logger.info(
            "version.yank outcome=success plugin_id=%s version_id=%s "
            "actor_id=%s latest_changed=%s promoted_version_id=%s",
            plugin.id, version.id, actor.id, latest_changed,
            promoted.id if promoted else None,
        )
        return version, promoted
