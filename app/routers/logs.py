"""
日志管理路由
提供日志查询和清理接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.time import utc_now
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.services.log_cleanup_service import log_cleanup_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/stats")
async def get_log_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取日志统计信息（需要 system:logs 权限）"""
    if not current_user.has_permission("system:logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:logs 权限"
        )
    
    stats = await log_cleanup_service.get_log_stats(db)
    return stats


@router.post("/cleanup")
async def cleanup_logs(
    log_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动清理日志（需要 system:logs 权限）
    
    Args:
        log_type: 日志类型 (review/sandbox/permission/all)，默认 all
    """
    if not current_user.has_permission("system:logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:logs 权限"
        )
    
    try:
        if log_type is None or log_type == "all":
            # 清理所有类型的日志
            result = await log_cleanup_service.cleanup_all_logs(db)
            return {
                "message": "日志清理完成",
                "deleted_count": result["total_deleted"],
                "details": result
            }
        else:
            # 清理指定类型的日志
            before_date = utc_now()
            deleted = await log_cleanup_service.cleanup_logs_by_date(
                db, log_type, before_date
            )
            return {
                "message": f"{log_type} 日志清理完成",
                "deleted_count": deleted,
                "log_type": log_type
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.post("/cleanup/by-date")
async def cleanup_logs_by_date(
    log_type: str,
    before_date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    按日期清理日志（需要 system:logs 权限）
    
    Args:
        log_type: 日志类型 (review/sandbox/permission)
        before_date: 删除此日期之前的日志
    """
    if not current_user.has_permission("system:logs"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:logs 权限"
        )
    
    try:
        deleted = await log_cleanup_service.cleanup_logs_by_date(
            db, log_type, before_date
        )
        return {
            "message": f"{log_type} 日志清理完成",
            "deleted_count": deleted,
            "log_type": log_type,
            "before_date": before_date.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/retention-settings")
async def get_retention_settings(
    current_user: User = Depends(get_current_user)
):
    """获取日志保留设置（需要 system:settings 权限）"""
    if not current_user.has_permission("system:settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 system:settings 权限"
        )
    
    from app.core.config import settings
    
    return {
        "review_log_retention_days": settings.REVIEW_LOG_RETENTION_DAYS,
        "sandbox_log_retention_days": settings.SANDBOX_LOG_RETENTION_DAYS,
        "permission_audit_retention_days": settings.PERMISSION_AUDIT_RETENTION_DAYS,
        "cleanup_interval_hours": settings.LOG_CLEANUP_INTERVAL_HOURS
    }
