from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User


class BootstrapService:
    @staticmethod
    async def ensure_schema_compatibility(db: AsyncSession) -> None:
        """Apply small SQLite-compatible schema additions for local auto-created DBs."""
        bind = db.get_bind()
        if bind and bind.dialect.name != "sqlite":
            return

        result = await db.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in result.fetchall()}

        if "must_change_password" not in columns:
            await db.execute(
                text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0")
            )
            await db.commit()

        if "email_verified_at" not in columns:
            await db.execute(
                text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME")
            )
            await db.commit()

    @staticmethod
    async def ensure_initial_admin(db: AsyncSession) -> None:
        result = await db.execute(
            select(func.count(User.id)).where(User.is_admin == True)
        )
        admin_count = result.scalar() or 0
        if admin_count > 0:
            return

        result = await db.execute(
            select(User).where(User.username == settings.INITIAL_ADMIN_USERNAME)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                display_name="Root",
                is_active=True,
                is_admin=True,
                must_change_password=True,
            )
            db.add(user)
        else:
            user.email = settings.INITIAL_ADMIN_EMAIL
            user.hashed_password = get_password_hash(settings.INITIAL_ADMIN_PASSWORD)
            user.display_name = user.display_name or "Root"
            user.is_active = True
            user.is_admin = True
            user.must_change_password = True

        await db.commit()
