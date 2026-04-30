from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "kid": jwt_key_manager.get_key_id()  # 添加密钥ID
    })
    
    # 使用当前主密钥签名
    secret_key = jwt_key_manager.get_current_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建 JWT 刷新令牌（使用当前主密钥）"""
    from app.core.jwt_key_manager import jwt_key_manager
    
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 刷新令牌7天有效期
    to_encode.update({
        "exp": expire,
        "type": "refresh",
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户（支持密钥轮换）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # 使用支持密钥轮换的解码方法
    payload = await decode_token_with_key_rotation(token, db)
    
    if payload is None:
        raise credentials_exception
    
    # 检查令牌类型
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # 查询用户
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
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
