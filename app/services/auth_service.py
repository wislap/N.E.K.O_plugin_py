import hashlib
import secrets
from datetime import timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.models.user import User
from app.models.auth_session import LoginAttempt, RefreshTokenSession
from app.core.time import utc_now
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    decode_token_with_key_rotation,
    get_password_hash
)
from app.schemas.user import UserCreate
from app.services.email_verification_service import email_verification_service
from app.services.transactions import commit_or_rollback


class AuthService:
    @staticmethod
    def _hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        return identifier.strip().lower()

    @staticmethod
    def validate_password_strength(password: str) -> None:
        if len(password) < 6:
            raise ValueError("密码长度至少需要 6 个字符")

    @staticmethod
    async def _ensure_login_not_locked(db: AsyncSession, identifier: str) -> None:
        normalized = AuthService._normalize_identifier(identifier)
        attempt = await db.scalar(
            select(LoginAttempt).where(LoginAttempt.identifier == normalized)
        )
        if attempt and attempt.locked_until and attempt.locked_until > utc_now():
            raise ValueError("登录失败次数过多，请稍后再试")

    @staticmethod
    async def _record_login_failure(db: AsyncSession, identifier: str) -> None:
        normalized = AuthService._normalize_identifier(identifier)
        now = utc_now()
        attempt = await db.scalar(
            select(LoginAttempt).where(LoginAttempt.identifier == normalized)
        )
        if attempt is None:
            attempt = LoginAttempt(identifier=normalized, first_failed_at=now)
            db.add(attempt)

        attempt.failed_count = (attempt.failed_count or 0) + 1
        attempt.last_failed_at = now
        attempt.updated_at = now
        if attempt.failed_count >= settings.AUTH_LOGIN_MAX_FAILURES:
            attempt.locked_until = now + timedelta(minutes=settings.AUTH_LOGIN_LOCKOUT_MINUTES)
        await db.commit()

    @staticmethod
    async def _clear_login_failures(db: AsyncSession, identifier: str) -> None:
        normalized = AuthService._normalize_identifier(identifier)
        attempt = await db.scalar(
            select(LoginAttempt).where(LoginAttempt.identifier == normalized)
        )
        if attempt:
            attempt.failed_count = 0
            attempt.first_failed_at = None
            attempt.last_failed_at = None
            attempt.locked_until = None
            attempt.updated_at = utc_now()
            await db.commit()

    @staticmethod
    async def _issue_refresh_token(
        db: AsyncSession,
        user_id: int,
        *,
        client_id: str | None = None,
    ) -> str:
        jti = secrets.token_urlsafe(32)
        token = create_refresh_token(data={"sub": str(user_id)}, jti=jti)
        now = utc_now()
        session = RefreshTokenSession(
            user_id=user_id,
            token_hash=AuthService._hash_refresh_token(token),
            jti=jti,
            issued_at=now,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            client_id=client_id,
            is_active=True,
        )
        db.add(session)
        await db.commit()
        return token
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """验证用户凭据"""
        await AuthService._ensure_login_not_locked(db, username)
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await AuthService._record_login_failure(db, username)
            return None
        
        if not verify_password(password, user.hashed_password):
            await AuthService._record_login_failure(db, username)
            return None
        
        # 更新最后登录时间
        user.last_login = utc_now()
        await db.commit()
        await AuthService._clear_login_failures(db, username)
        
        return user
    
    @staticmethod
    async def register_user(
        db: AsyncSession, 
        user_data: UserCreate
    ) -> Tuple[User, bool]:
        """注册用户并发送邮箱验证邮件。"""
        AuthService.validate_password_strength(user_data.password)
        await email_verification_service.ensure_delivery_available(db)
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("邮箱已存在")
        
        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            display_name=user_data.display_name
        )

        db.add(user)
        await db.flush()
        _token, raw_verification_token = await email_verification_service.issue_for_user(
            db,
            user,
            commit=False,
        )

        try:
            verification_email_sent = await email_verification_service.send_verification_email(
                db,
                user,
                raw_verification_token,
            )
        except Exception:
            await db.rollback()
            raise

        if not verification_email_sent:
            await db.rollback()
            raise ValueError("验证邮件发送失败，请稍后再试或联系管理员")

        await db.commit()
        await db.refresh(user)

        return user, verification_email_sent
    
    @staticmethod
    async def login_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Tuple[User, str, str]:
        """用户登录"""
        user = await AuthService.authenticate_user(db, username, password)
        if not user:
            raise ValueError("用户名或密码错误")
        
        if not user.is_active:
            raise ValueError("用户已被禁用")

        if not user.is_email_verified:
            raise ValueError("请先完成邮箱验证后再登录")
        
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = await AuthService._issue_refresh_token(db, user.id)
        
        return user, access_token, refresh_token
    
    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
        """使用刷新令牌获取新的访问令牌，并轮换 refresh token。"""
        payload = await decode_token_with_key_rotation(refresh_token, db)
        if not payload:
            raise ValueError("无效的刷新令牌")
        
        if payload.get("type") != "refresh":
            raise ValueError("无效的令牌类型")
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id:
            raise ValueError("无效的令牌")
        if not jti:
            raise ValueError("无效的刷新令牌")

        session = await db.scalar(
            select(RefreshTokenSession).where(
                RefreshTokenSession.jti == jti,
                RefreshTokenSession.token_hash == AuthService._hash_refresh_token(refresh_token),
            )
        )
        if (
            not session
            or not session.is_active
            or session.revoked_at is not None
            or session.expires_at <= utc_now()
        ):
            raise ValueError("刷新令牌已失效")

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("用户不存在或已被禁用")
        
        new_refresh_token = await AuthService._issue_refresh_token(
            db,
            int(user_id),
            client_id=session.client_id,
        )
        new_payload = await decode_token_with_key_rotation(new_refresh_token, db)
        session.is_active = False
        session.revoked_at = utc_now()
        session.replaced_by_jti = new_payload.get("jti") if new_payload else None
        session.updated_at = utc_now()
        await db.commit()

        return create_access_token(data={"sub": user_id}), new_refresh_token

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> bool:
        payload = await decode_token_with_key_rotation(refresh_token, db)
        if not payload or payload.get("type") != "refresh":
            return False

        jti = payload.get("jti")
        if not jti:
            return False

        session = await db.scalar(
            select(RefreshTokenSession).where(
                RefreshTokenSession.jti == jti,
                RefreshTokenSession.token_hash == AuthService._hash_refresh_token(refresh_token),
            )
        )
        if not session or not session.is_active:
            return False

        session.is_active = False
        session.revoked_at = utc_now()
        session.updated_at = utc_now()
        await db.commit()
        return True

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str
    ) -> User:
        """修改当前用户密码"""
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("当前密码错误")
        AuthService.validate_password_strength(new_password)

        user.hashed_password = get_password_hash(new_password)
        user.must_change_password = False
        user.updated_at = utc_now()
        now = utc_now()
        await db.execute(
            update(RefreshTokenSession)
            .where(
                RefreshTokenSession.user_id == user.id,
                RefreshTokenSession.is_active == True,
            )
            .values(is_active=False, revoked_at=now, updated_at=now)
        )
        await db.commit()
        await db.refresh(user)
        return user
