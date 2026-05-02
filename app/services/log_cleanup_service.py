"""
日志清理服务
自动清理过期的审核日志和沙箱日志
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.core.config import settings
from app.core.time import utc_now
from app.models.plugin_review import PluginReview, PluginReviewHistory
from app.models.ai_sandbox_log import AISandboxLog
from app.models.permission import PermissionAuditLog

logger = logging.getLogger(__name__)


class LogCleanupService:
    """
    日志清理服务
    
    功能：
    1. 自动清理过期的审核日志
    2. 自动清理过期的沙箱日志
    3. 自动清理过期的权限审计日志
    4. 支持手动触发清理
    """
    
    def __init__(self):
        # 从配置读取保留时间（天）
        self.review_log_retention_days = getattr(settings, 'REVIEW_LOG_RETENTION_DAYS', 90)
        self.sandbox_log_retention_days = getattr(settings, 'SANDBOX_LOG_RETENTION_DAYS', 30)
        self.permission_audit_retention_days = getattr(settings, 'PERMISSION_AUDIT_RETENTION_DAYS', 180)
        
        # 自动清理间隔（小时）
        self.cleanup_interval_hours = getattr(settings, 'LOG_CLEANUP_INTERVAL_HOURS', 24)
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_auto_cleanup(self):
        """启动自动清理任务"""
        if self._running:
            logger.warning("自动清理任务已在运行")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"日志自动清理服务已启动，清理间隔: {self.cleanup_interval_hours}小时")
    
    async def stop_auto_cleanup(self):
        """停止自动清理任务"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("日志自动清理服务已停止")
    
    async def _cleanup_loop(self):
        """清理循环"""
        from app.core.database import AsyncSessionLocal
        
        # 首次运行时先等待一个周期，避免在应用启动时立即执行
        logger.info(f"日志清理任务将在 {self.cleanup_interval_hours} 小时后首次执行")
        await asyncio.sleep(self.cleanup_interval_hours * 3600)
        
        while self._running:
            try:
                # 创建新的数据库会话执行清理
                async with AsyncSessionLocal() as db:
                    # 执行清理
                    await self.cleanup_all_logs(db)
                
                # 等待下一次清理
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"日志清理循环出错: {e}")
                await asyncio.sleep(3600)  # 出错后1小时重试
    
    async def cleanup_all_logs(self, db: Optional[AsyncSession] = None) -> dict:
        """
        清理所有类型的日志
        
        Returns:
            清理统计信息
        """
        stats = {
            "review_logs_deleted": 0,
            "sandbox_logs_deleted": 0,
            "permission_audit_logs_deleted": 0,
            "total_deleted": 0,
            "cleanup_time": utc_now().isoformat()
        }
        
        try:
            # 清理审核日志
            review_deleted = await self.cleanup_review_logs(db)
            stats["review_logs_deleted"] = review_deleted
            
            # 清理沙箱日志
            sandbox_deleted = await self.cleanup_sandbox_logs(db)
            stats["sandbox_logs_deleted"] = sandbox_deleted
            
            # 清理权限审计日志
            permission_deleted = await self.cleanup_permission_audit_logs(db)
            stats["permission_audit_logs_deleted"] = permission_deleted
            
            stats["total_deleted"] = review_deleted + sandbox_deleted + permission_deleted
            
            logger.info(f"日志清理完成: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"日志清理失败: {e}")
            raise
    
    async def cleanup_review_logs(self, db: AsyncSession) -> int:
        """
        清理过期的插件审核日志
        
        Returns:
            删除的记录数
        """
        cutoff_date = utc_now() - timedelta(days=self.review_log_retention_days)
        
        # 删除审核历史记录
        result = await db.execute(
            delete(PluginReviewHistory).where(
                PluginReviewHistory.created_at < cutoff_date
            )
        )
        deleted_history = result.rowcount
        
        # 删除已完成的审核记录（保留 pending 和 manual_review 状态的）
        result = await db.execute(
            delete(PluginReview).where(
                and_(
                    PluginReview.created_at < cutoff_date,
                    PluginReview.stage.in_(["approved", "rejected"])
                )
            )
        )
        deleted_reviews = result.rowcount
        
        await db.commit()
        
        total_deleted = deleted_history + deleted_reviews
        if total_deleted > 0:
            logger.info(f"清理审核日志: 删除 {total_deleted} 条记录 (历史: {deleted_history}, 审核: {deleted_reviews})")
        
        return total_deleted
    
    async def cleanup_sandbox_logs(self, db: AsyncSession) -> int:
        """
        清理过期的沙箱执行日志
        
        Returns:
            删除的记录数
        """
        cutoff_date = utc_now() - timedelta(days=self.sandbox_log_retention_days)
        
        result = await db.execute(
            delete(AISandboxLog).where(
                AISandboxLog.created_at < cutoff_date
            )
        )
        deleted_count = result.rowcount
        await db.commit()
        
        if deleted_count > 0:
            logger.info(f"清理沙箱日志: 删除 {deleted_count} 条记录")
        
        return deleted_count
    
    async def cleanup_permission_audit_logs(self, db: AsyncSession) -> int:
        """
        清理过期的权限审计日志
        
        Returns:
            删除的记录数
        """
        cutoff_date = utc_now() - timedelta(days=self.permission_audit_retention_days)
        
        result = await db.execute(
            delete(PermissionAuditLog).where(
                PermissionAuditLog.created_at < cutoff_date
            )
        )
        deleted_count = result.rowcount
        await db.commit()
        
        if deleted_count > 0:
            logger.info(f"清理权限审计日志: 删除 {deleted_count} 条记录")
        
        return deleted_count
    
    async def get_log_stats(self, db: AsyncSession) -> dict:
        """
        获取日志统计信息
        
        Returns:
            各类日志的统计信息
        """
        # 审核日志统计
        from sqlalchemy import func
        
        result = await db.execute(select(func.count()).select_from(PluginReview))
        review_count = result.scalar()
        
        result = await db.execute(select(func.count()).select_from(PluginReviewHistory))
        review_history_count = result.scalar()
        
        # 沙箱日志统计
        result = await db.execute(select(func.count()).select_from(AISandboxLog))
        sandbox_count = result.scalar()
        
        # 权限审计日志统计
        result = await db.execute(select(func.count()).select_from(PermissionAuditLog))
        permission_audit_count = result.scalar()
        
        # 计算即将被清理的日志数量
        cutoff_review = utc_now() - timedelta(days=self.review_log_retention_days)
        cutoff_sandbox = utc_now() - timedelta(days=self.sandbox_log_retention_days)
        cutoff_permission = utc_now() - timedelta(days=self.permission_audit_retention_days)
        
        result = await db.execute(
            select(func.count()).select_from(PluginReviewHistory)
            .where(PluginReviewHistory.created_at < cutoff_review)
        )
        review_expiring = result.scalar()
        
        result = await db.execute(
            select(func.count()).select_from(AISandboxLog)
            .where(AISandboxLog.created_at < cutoff_sandbox)
        )
        sandbox_expiring = result.scalar()
        
        result = await db.execute(
            select(func.count()).select_from(PermissionAuditLog)
            .where(PermissionAuditLog.created_at < cutoff_permission)
        )
        permission_expiring = result.scalar()
        
        return {
            "current_counts": {
                "plugin_reviews": review_count,
                "plugin_review_history": review_history_count,
                "sandbox_logs": sandbox_count,
                "permission_audit_logs": permission_audit_count,
                "total": review_count + review_history_count + sandbox_count + permission_audit_count
            },
            "retention_settings": {
                "review_logs_days": self.review_log_retention_days,
                "sandbox_logs_days": self.sandbox_log_retention_days,
                "permission_audit_days": self.permission_audit_retention_days
            },
            "expiring_soon": {
                "review_logs": review_expiring,
                "sandbox_logs": sandbox_expiring,
                "permission_audit_logs": permission_expiring,
                "total": review_expiring + sandbox_expiring + permission_expiring
            }
        }
    
    async def cleanup_logs_by_date(
        self,
        db: AsyncSession,
        log_type: str,
        before_date: datetime
    ) -> int:
        """
        按日期清理指定类型的日志（手动清理）
        
        Args:
            db: 数据库会话
            log_type: 日志类型 (review/sandbox/permission)
            before_date: 删除此日期之前的日志
            
        Returns:
            删除的记录数
        """
        if log_type == "review":
            result = await db.execute(
                delete(PluginReviewHistory).where(
                    PluginReviewHistory.created_at < before_date
                )
            )
            deleted = result.rowcount
            await db.commit()
            logger.info(f"手动清理审核历史日志: 删除 {deleted} 条记录")
            return deleted
            
        elif log_type == "sandbox":
            result = await db.execute(
                delete(AISandboxLog).where(
                    AISandboxLog.created_at < before_date
                )
            )
            deleted = result.rowcount
            await db.commit()
            logger.info(f"手动清理沙箱日志: 删除 {deleted} 条记录")
            return deleted
            
        elif log_type == "permission":
            result = await db.execute(
                delete(PermissionAuditLog).where(
                    PermissionAuditLog.created_at < before_date
                )
            )
            deleted = result.rowcount
            await db.commit()
            logger.info(f"手动清理权限审计日志: 删除 {deleted} 条记录")
            return deleted
            
        else:
            raise ValueError(f"未知的日志类型: {log_type}")


# 全局日志清理服务实例
log_cleanup_service = LogCleanupService()
