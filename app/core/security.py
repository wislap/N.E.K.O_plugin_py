from datetime import datetime, timedelta
import secrets
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.time import utc_now
from app.core.database import get_db
from app.models.user import User
from app.models.permission import PermissionGroup

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌（使用当前主密钥）"""
    from app.core.jwt_key_manager import jwt_key_manager
    
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "kid": jwt_key_manager.get_key_id()  # 添加密钥ID
    })
    
    # 使用当前主密钥签名
    secret_key = jwt_key_manager.get_current_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, jti: str | None = None) -> str:
    """创建 JWT 刷新令牌（使用当前主密钥）"""
    from app.core.jwt_key_manager import jwt_key_manager
    
    to_encode = data.copy()
    expire = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": jti or secrets.token_urlsafe(32),
        "kid": jwt_key_manager.get_key_id()  # 添加密钥ID
    })
    
    # 使用当前主密钥签名
    secret_key = jwt_key_manager.get_current_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT 令牌（使用配置密钥，向后兼容）"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def decode_token_with_key_rotation(token: str, db: AsyncSession) -> Optional[dict]:
    """
    解码 JWT 令牌（支持密钥轮换）
    首先尝试使用当前密钥，如果失败则根据 kid 查找对应密钥
    """
    from app.core.jwt_key_manager import jwt_key_manager
    
    # 首先尝试不解码头部获取 kid
    try:
        # 解析 JWT 头部获取密钥ID
        header = jwt.get_unverified_header(token)
        key_id = header.get("kid")
        
        if key_id:
            # 使用对应密钥验证
            secret = await jwt_key_manager.get_key_by_id(db, key_id)
            if secret:
                try:
                    payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
                    return payload
                except JWTError:
                    pass
    except Exception:
        pass
    
    # 尝试使用当前主密钥
    try:
        secret_key = jwt_key_manager.get_current_key()
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        pass
    
    # 最后尝试使用配置中的密钥（向后兼容）
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户（支持密钥轮换）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if credentials is None:
        if settings.debug_auth_enabled:
            return await get_or_create_debug_user(db)
        raise credentials_exception
    
    token = credentials.credentials
    
    # 使用支持密钥轮换的解码方法
    payload = await decode_token_with_key_rotation(token, db)
    
    if payload is None:
        if settings.debug_auth_enabled:
            return await get_or_create_debug_user(db)
        raise credentials_exception
    
    # 检查令牌类型
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # 查询用户
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.permission_groups).selectinload(PermissionGroup.permissions),
            selectinload(User.permission_groups).selectinload(PermissionGroup.inherited_groups),
            selectinload(User.permission_groups).selectinload(PermissionGroup.parent),
        )
        .where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Return the logged-in user when a valid bearer token is present."""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Require a verified email address for creator/publishing actions."""
    if current_user.is_admin or current_user.email_verified_at is not None:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="请先完成邮箱验证",
    )


async def get_or_create_debug_user(db: AsyncSession) -> User:
    """获取或创建调试用户。仅在 settings.debug_auth_enabled 为 True 时调用。"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.permission_groups).selectinload(PermissionGroup.permissions),
            selectinload(User.permission_groups).selectinload(PermissionGroup.inherited_groups),
            selectinload(User.permission_groups).selectinload(PermissionGroup.parent),
        )
        .where(User.username == settings.DEBUG_AUTH_USERNAME)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            username=settings.DEBUG_AUTH_USERNAME,
            email=settings.DEBUG_AUTH_EMAIL,
            hashed_password=pwd_context.hash("debug-password"),
            display_name="调试用户",
            is_active=True,
            is_admin=settings.DEBUG_AUTH_IS_ADMIN,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif (
        user.email != settings.DEBUG_AUTH_EMAIL
        or user.is_admin != settings.DEBUG_AUTH_IS_ADMIN
        or not user.is_active
    ):
        user.email = settings.DEBUG_AUTH_EMAIL
        user.is_admin = settings.DEBUG_AUTH_IS_ADMIN
        user.is_active = True
        await db.commit()
        await db.refresh(user)

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活"
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


class RoleChecker:
    """角色检查依赖类"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user: User = Depends(get_current_user)):
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return user


class PermissionChecker:
    """权限检查依赖类"""
    
    def __init__(self, permission_code: str):
        self.permission_code = permission_code
    
    def __call__(self, user: User = Depends(get_current_user)):
        if not user.has_permission(self.permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {self.permission_code}"
            )
        return user


class AnyPermissionChecker:
    """任意权限检查依赖类"""
    
    def __init__(self, permission_codes: list):
        self.permission_codes = permission_codes
    
    def __call__(self, user: User = Depends(get_current_user)):
        if not user.has_any_permission(self.permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下任意权限: {', '.join(self.permission_codes)}"
            )
        return user


class AllPermissionsChecker:
    """所有权限检查依赖类"""
    
    def __init__(self, permission_codes: list):
        self.permission_codes = permission_codes
    
    def __call__(self, user: User = Depends(get_current_user)):
        if not user.has_all_permissions(self.permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下所有权限: {', '.join(self.permission_codes)}"
            )
        return user


def require_permission(permission_code: str):
    """装饰器：需要指定权限"""
    return Depends(PermissionChecker(permission_code))


def require_any_permission(permission_codes: list):
    """装饰器：需要任意一个权限"""
    return Depends(AnyPermissionChecker(permission_codes))


def require_all_permissions(permission_codes: list):
    """装饰器：需要所有权限"""
    return Depends(AllPermissionsChecker(permission_codes))
