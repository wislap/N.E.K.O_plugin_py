"""把 `latest_version` 子对象挂到 Plugin 实例上。

Plugin 列表 / 详情接口在响应序列化前调用 `attach_latest_version` 一次，
把 (plugin, channel='stable') 的 is_latest 行批量取出后挂到每个 plugin
的 `__dict__["latest_version"]`，让 Pydantic schema (`from_attributes=True`)
能直接读出。

为什么不用 SQLAlchemy `column_property` / `hybrid_property`：
- 那两条路径都需要在 ORM 层定义 join 子查询，写起来啰嗦且不利于
  按调用方传入的 channel 切换；
- 临时属性挂法跨 SQLAlchemy 会话边界失效，本服务保证只在响应序列化
  前同会话内挂载，实际无副作用。
"""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin
from app.models.version import Version


async def attach_latest_version(
    db: AsyncSession,
    plugins: Iterable[Plugin],
    *,
    channel: str = "stable",
) -> None:
    """对一批 Plugin 实例批量挂 `latest_version`（is_latest=true & 非 yanked）。

    传入空列表 / 元组时早返回，避免一次空 IN 查询。

    R0 灵魂条款约束：本投影只会暴露 `package_url` 与 `package_sha256` 都
    非空的版本；这两个字段空（legacy 数据 / 未经过 publish-from-release）
    的行会被过滤为 `latest_version=None`，等价于"该 plugin 暂无可下载版本"。
    """
    plugin_list = list(plugins)
    if not plugin_list:
        return

    plugin_ids = [p.id for p in plugin_list]
    stmt = select(Version).where(
        Version.plugin_id.in_(plugin_ids),
        Version.channel == channel,
        Version.is_latest.is_(True),
        Version.yanked_at.is_(None),
        Version.package_url.is_not(None),
        Version.package_url != "",
        Version.package_sha256.is_not(None),
        Version.package_sha256 != "",
    )
    rows = (await db.execute(stmt)).scalars().all()
    by_plugin: dict[int, Version] = {row.plugin_id: row for row in rows}

    for plugin in plugin_list:
        plugin.__dict__["latest_version"] = by_plugin.get(plugin.id)


async def attach_latest_version_single(
    db: AsyncSession,
    plugin: Optional[Plugin],
    *,
    channel: str = "stable",
) -> None:
    """单条 plugin 的便捷重载，None 时直接 no-op。"""
    if plugin is None:
        return
    await attach_latest_version(db, [plugin], channel=channel)


__all__ = [
    "attach_latest_version",
    "attach_latest_version_single",
]
