from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.user import User, UserUpdate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/users", response_model=PaginatedResponse[User])
async def list_users(
    q: str | None = Query(None, description="搜索用户名、邮箱或昵称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表（需要管理员权限），支持分页和搜索
    """
    filters = []
    if q:
        keyword = f"%{q}%"
        filters.append(
            or_(
                UserModel.username.ilike(keyword),
                UserModel.email.ilike(keyword),
                UserModel.display_name.ilike(keyword),
            )
        )

    query = select(UserModel)
    count_query = select(func.count(UserModel.id))
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
    )
    users = list(result.scalars().all())
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


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
    if user.id != current_user.id and not current_user.is_admin:
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
    
    if user.id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此用户"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    admin_only_fields = {"username", "email", "is_active", "is_admin"}
    if not current_user.is_admin:
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

    if current_user.is_admin and user.is_admin:
        admin_count = (
            await db.execute(
                select(func.count(UserModel.id)).where(
                    UserModel.is_admin == True,
                    UserModel.is_active == True,
                )
            )
        ).scalar() or 0
        removing_last_admin = (
            update_dict.get("is_admin") is False
            or update_dict.get("is_active") is False
        )
        if admin_count <= 1 and removing_last_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能禁用或降级最后一个管理员"
            )

    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户（需要管理员权限）
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

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录用户"
        )

    if user.is_admin and user.is_active:
        admin_count = (
            await db.execute(
                select(func.count(UserModel.id)).where(
                    UserModel.is_admin == True,
                    UserModel.is_active == True,
                )
            )
        ).scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除最后一个管理员"
            )
    
    await db.delete(user)
    await db.commit()
    
    return MessageResponse(message="用户已删除")


