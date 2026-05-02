from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.user import User as UserModel
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import User, UserUpdate

router = APIRouter(prefix="/users", tags=["admin-users"])
require_user_management = PermissionChecker("system:user")


@router.get("", response_model=PaginatedResponse[User])
async def list_users(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(require_user_management),
    db: AsyncSession = Depends(get_db),
):
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
    total_pages = (total + page_size - 1) // page_size
    result = await db.execute(
        query.order_by(UserModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PaginatedResponse(
        items=list(result.scalars().all()),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    current_user: UserModel = Depends(require_user_management),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    update_dict = update_data.model_dump(exclude_unset=True)
    if "username" in update_dict and update_dict["username"] != user.username:
        existing = await db.execute(
            select(UserModel).where(UserModel.username == update_dict["username"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    if "email" in update_dict and update_dict["email"] != user.email:
        existing = await db.execute(
            select(UserModel).where(UserModel.email == update_dict["email"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    if user.is_admin:
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
                detail="不能禁用或降级最后一个管理员",
            )

    for field, value in update_dict.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: UserModel = Depends(require_user_management),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录用户")
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除最后一个管理员")

    await db.delete(user)
    await db.commit()
    return MessageResponse(message="用户已删除")
