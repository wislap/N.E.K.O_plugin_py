import hashlib
import hmac
import secrets
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import utc_now
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.services.email_service import email_service
from app.services.transactions import commit_or_rollback


class EmailVerificationService:
    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def build_verification_url(token: str) -> str:
        base_url = settings.FRONTEND_BASE_URL.rstrip("/")
        return f"{base_url}/#/verify-email?token={quote(token)}"

    async def create_token(self, db: AsyncSession, user: User) -> tuple[EmailVerificationToken, str]:
        raw_token = secrets.token_urlsafe(32)
        now = utc_now()
        token = EmailVerificationToken(
            user_id=user.id,
            email=user.email,
            token_hash=self.hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
            created_at=now,
            is_active=True,
        )
        db.add(token)
        await db.flush()
        return token, raw_token

    async def issue_for_user(
        self,
        db: AsyncSession,
        user: User,
        commit: bool = True,
    ) -> tuple[EmailVerificationToken, str]:
        async def issue() -> tuple[EmailVerificationToken, str]:
            await db.execute(
                update(EmailVerificationToken)
                .where(
                    EmailVerificationToken.user_id == user.id,
                    EmailVerificationToken.is_active == True,
                    EmailVerificationToken.used_at.is_(None),
                )
                .values(is_active=False)
            )
            return await self.create_token(db, user)

        if not commit:
            return await issue()

        async with commit_or_rollback(db):
            token, raw_token = await issue()

        await db.refresh(token)
        return token, raw_token

    async def send_verification_email(
        self,
        db: AsyncSession,
        user: User,
        raw_token: str,
    ) -> bool:
        email_service.set_db_session(db)
        sent = await email_service.send_email_verification(
            to_email=user.email,
            username=user.display_name or user.username,
            verification_url=self.build_verification_url(raw_token),
            expires_minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
        )
        if sent:
            token_hash = self.hash_token(raw_token)
            result = await db.execute(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token_hash == token_hash,
                    EmailVerificationToken.user_id == user.id,
                )
            )
            token = result.scalar_one_or_none()
            if token:
                async with commit_or_rollback(db):
                    token.sent_at = utc_now()
        return sent

    async def resend(self, db: AsyncSession, user: User) -> tuple[bool, bool]:
        if user.email_verified_at is not None:
            return True, False

        now = utc_now()
        result = await db.execute(
            select(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.is_active == True,
                EmailVerificationToken.used_at.is_(None),
            )
            .order_by(EmailVerificationToken.created_at.desc())
        )
        latest = result.scalars().first()
        cooldown = timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS)
        if latest and latest.created_at and latest.created_at + cooldown > now:
            raise ValueError("验证邮件发送过于频繁，请稍后再试")

        token, raw_token = await self.issue_for_user(db, user)
        sent = await self.send_verification_email(db, user, raw_token)
        return False, sent

    async def verify(self, db: AsyncSession, raw_token: str) -> User:
        token_hash = self.hash_token(raw_token)
        result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.is_active == True,
                EmailVerificationToken.used_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if not token or not hmac.compare_digest(token.token_hash, token_hash):
            raise ValueError("验证链接无效或已使用")

        if token.expires_at < utc_now():
            async with commit_or_rollback(db):
                token.is_active = False
            raise ValueError("验证链接已过期，请重新发送验证邮件")

        user = await db.get(User, token.user_id)
        if not user:
            raise ValueError("用户不存在")

        async with commit_or_rollback(db):
            user.email_verified_at = utc_now()
            user.updated_at = utc_now()
            token.used_at = utc_now()
            token.is_active = False

        await db.refresh(user)
        return user


email_verification_service = EmailVerificationService()
