from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.core.time import utc_now
from app.models.user import User
from app.services.log_cleanup_service import log_cleanup_service

router = APIRouter(prefix="/logs", tags=["admin-logs"])
require_log_access = PermissionChecker("system:logs")
require_settings_access = PermissionChecker("system:settings")


class LogCleanupRequest(BaseModel):
    log_type: Optional[str] = "all"


class LogCleanupByDateRequest(BaseModel):
    log_type: str
    before_date: datetime


@router.get("/stats")
async def get_log_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_log_access),
):
    return await log_cleanup_service.get_log_stats(db)


@router.post("/cleanup")
async def cleanup_logs(
    data: LogCleanupRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_log_access),
):
    log_type = (data.log_type if data else "all") or "all"
    try:
        if log_type == "all":
            result = await log_cleanup_service.cleanup_all_logs(db)
            return {
                "message": "日志清理完成",
                "deleted_count": result["total_deleted"],
                "details": result,
            }

        deleted = await log_cleanup_service.cleanup_logs_by_date(db, log_type, utc_now())
        return {
            "message": f"{log_type} 日志清理完成",
            "deleted_count": deleted,
            "log_type": log_type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.post("/cleanup/by-date")
async def cleanup_logs_by_date(
    data: LogCleanupByDateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_log_access),
):
    try:
        deleted = await log_cleanup_service.cleanup_logs_by_date(
            db,
            data.log_type,
            data.before_date,
        )
        return {
            "message": f"{data.log_type} 日志清理完成",
            "deleted_count": deleted,
            "log_type": data.log_type,
            "before_date": data.before_date.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/retention-settings")
async def get_retention_settings(
    current_user: User = Depends(require_settings_access),
):
    from app.core.config import settings

    return {
        "review_log_retention_days": settings.REVIEW_LOG_RETENTION_DAYS,
        "sandbox_log_retention_days": settings.SANDBOX_LOG_RETENTION_DAYS,
        "permission_audit_retention_days": settings.PERMISSION_AUDIT_RETENTION_DAYS,
        "cleanup_interval_hours": settings.LOG_CLEANUP_INTERVAL_HOURS,
    }
