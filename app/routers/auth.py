from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_or_create_debug_user, create_access_token, create_refresh_token
from app.services.auth_service import AuthService
from app.services.email_verification_service import email_verification_service
from app.schemas.user import UserCreate, UserLogin, User, Token, PasswordChange, RefreshTokenRequest
from app.schemas.common import MessageResponse

router = APIRouter()


def serialize_user(user) -> dict:
    return jsonable_encoder(User.model_validate(user))


@router.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册
    """
    try:
        user, access_token, refresh_token, verification_email_sent = await AuthService.register_user(db, user_data)
        return {
            "user": serialize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "verification_email_sent": verification_email_sent
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/login", response_model=dict)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    """
    try:
        user, access_token, refresh_token = await AuthService.login_user(
            db, login_data.username, login_data.password
        )
        return {
            "user": serialize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/auth/verify-email", response_model=User)
async def verify_email(
    token: str = Query(..., min_length=16),
    db: AsyncSession = Depends(get_db)
):
    """
    使用邮件链接中的 token 完成邮箱验证。
    """
    try:
        user = await email_verification_service.verify(db, token)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/resend-verification-email", response_model=dict)
async def resend_verification_email(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    为当前用户重新发送邮箱验证邮件。
    """
    try:
        already_verified, sent = await email_verification_service.resend(db, current_user)
        return {
            "already_verified": already_verified,
            "verification_email_sent": sent,
            "message": "邮箱已验证" if already_verified else ("验证邮件已发送" if sent else "邮件服务未启用，暂未发送")
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )


@router.post("/auth/debug-login", response_model=dict)
async def debug_login(
    db: AsyncSession = Depends(get_db)
):
    """
    调试登录。仅在 ENVIRONMENT=development 且 DEBUG_AUTH_ENABLED=true 时可用。
    """
    if not settings.debug_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="调试登录未启用"
        )

    user = await get_or_create_debug_user(db)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {
        "user": serialize_user(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest | None = Body(None),
    refresh_token: str | None = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新访问令牌
    """
    try:
        token_value = refresh_data.refresh_token if refresh_data else refresh_token
        if not token_value:
            raise ValueError("缺少刷新令牌")
        new_access_token = await AuthService.refresh_access_token(db, token_value)
        return Token(access_token=new_access_token, token_type="bearer")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/auth/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    """
    return current_user


@router.post("/auth/change-password", response_model=User)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改当前用户密码。首次 root 登录必须调用此接口完成改密。
    """
    try:
        user = await AuthService.change_password(
            db,
            current_user,
            password_data.current_password,
            password_data.new_password
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出（客户端需要清除令牌）
    """
    # 这里可以实现令牌黑名单等逻辑
    return MessageResponse(message="登出成功")
