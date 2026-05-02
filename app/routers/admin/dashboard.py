from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.time import utc_now
from app.models.plugin import Plugin, PluginStatus
from app.models.user import User


router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])

ADMIN_DASHBOARD_PERMISSIONS = [
    "plugin:review",
    "system:user",
    "system:permission",
    "system:smtp",
    "system:settings",
    "system:logs",
    "plugin:category",
    "plugin:zone",
    "plugin:signature",
]


class DashboardStats(BaseModel):
    totalUsers: int = 0
    totalPlugins: int = 0
    pendingPlugins: int = 0
    approvedPlugins: int = 0
    rejectedPlugins: int = 0
    recentUsers: int = 0
    recentPlugins: int = 0


def can_access(current_user: User, permission: str) -> bool:
    return current_user.is_admin or current_user.has_permission(permission)


async def count_query(db: AsyncSession, statement) -> int:
    result = await db.execute(statement)
    return result.scalar() or 0


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.has_any_permission(ADMIN_DASHBOARD_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有访问管理后台统计的权限",
        )

    stats = DashboardStats()
    week_ago = utc_now() - timedelta(days=7)

    if can_access(current_user, "system:user"):
        stats.totalUsers = await count_query(db, select(func.count(User.id)))
        stats.recentUsers = await count_query(
            db,
            select(func.count(User.id)).where(User.created_at >= week_ago),
        )

    if can_access(current_user, "plugin:review"):
        status_rows = await db.execute(
            select(Plugin.status, func.count(Plugin.id)).group_by(Plugin.status)
        )
        counts = {row[0]: row[1] for row in status_rows.all()}
        stats.totalPlugins = sum(counts.values())
        stats.pendingPlugins = counts.get(PluginStatus.PENDING, 0)
        stats.approvedPlugins = counts.get(PluginStatus.APPROVED, 0)
        stats.rejectedPlugins = counts.get(PluginStatus.REJECTED, 0)
        stats.recentPlugins = await count_query(
            db,
            select(func.count(Plugin.id)).where(Plugin.created_at >= week_ago),
        )

    return stats
