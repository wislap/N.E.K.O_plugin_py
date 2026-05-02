from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.notification import Notification
from app.models.user import User


class NotificationService:
    """站内通知服务。"""

    @staticmethod
    def add(
        db: AsyncSession,
        *,
        user_id: int,
        type: str,
        title: str,
        content: str | None = None,
        target_url: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            target_url=target_url,
        )
        db.add(notification)
        return notification

    @staticmethod
    async def notify_admins(
        db: AsyncSession,
        *,
        type: str,
        title: str,
        content: str | None = None,
        target_url: str | None = None,
    ) -> None:
        result = await db.execute(
            select(User.id).where(User.is_admin == True, User.is_active == True)
        )
        for admin_id in result.scalars().all():
            NotificationService.add(
                db,
                user_id=admin_id,
                type=type,
                title=title,
                content=content,
                target_url=target_url,
            )

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: int,
        *,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        result = await db.execute(
            query.order_by(Notification.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> Notification | None:
        notification = await db.get(Notification, notification_id)
        if not notification or notification.user_id != user_id:
            return None
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = utc_now()
            await db.commit()
            await db.refresh(notification)
        return notification

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=utc_now())
        )
        await db.commit()
        return result.rowcount or 0
