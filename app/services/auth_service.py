from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
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
    async def authenticate_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """验证用户凭据"""
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # 更新最后登录时间
        user.last_login = utc_now()
        await db.commit()
        
        return user
    
    @staticmethod
    async def register_user(
        db: AsyncSession, 
        user_data: UserCreate
    ) -> Tuple[User, str, str, bool]:
        """注册用户并返回令牌"""
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
        
        async with commit_or_rollback(db):
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

            # 生成令牌
            access_token = create_access_token(data={"sub": str(user.id)})
            refresh_token = create_refresh_token(data={"sub": str(user.id)})

        await db.refresh(user)

        verification_email_sent = await email_verification_service.send_verification_email(
            db,
            user,
            raw_verification_token,
        )

        return user, access_token, refresh_token, verification_email_sent
    
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
        
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return user, access_token, refresh_token
    
    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
        """使用刷新令牌获取新的访问令牌"""
        payload = await decode_token_with_key_rotation(refresh_token, db)
        if not payload:
            raise ValueError("无效的刷新令牌")
        
        if payload.get("type") != "refresh":
            raise ValueError("无效的令牌类型")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("无效的令牌")

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("用户不存在或已被禁用")
        
        return create_access_token(data={"sub": user_id})

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

        user.hashed_password = get_password_hash(new_password)
        user.must_change_password = False
        user.updated_at = utc_now()
        await db.commit()
        await db.refresh(user)
        return user
