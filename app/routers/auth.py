from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_or_create_debug_user, create_access_token, create_refresh_token
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserLogin, User, Token, PasswordChange
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
        user, access_token, refresh_token = await AuthService.register_user(db, user_data)
        return {
            "user": serialize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
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
async def refresh_token(refresh_token: str):
    """
    刷新访问令牌
    """
    try:
        new_access_token = AuthService.refresh_access_token(refresh_token)
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
