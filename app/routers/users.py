from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.user import User, UserUpdate
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户详情
    """
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看此用户"
        )
    
    return user


@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户信息（需要本人或管理员权限）
    """
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此用户"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    admin_only_fields = {"username", "email", "is_active", "is_admin"}
    update_dict = {
        key: value for key, value in update_dict.items()
        if key not in admin_only_fields
    }

    if "username" in update_dict and update_dict["username"] != user.username:
        existing = await db.execute(
            select(UserModel).where(UserModel.username == update_dict["username"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

    if "email" in update_dict and update_dict["email"] != user.email:
        existing = await db.execute(
            select(UserModel).where(UserModel.email == update_dict["email"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在"
            )

    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


