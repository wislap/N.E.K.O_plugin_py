from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.user import User, UserCreate, UserUpdate
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


@router.get("/users/username/{username}", response_model=User)
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """
    通过用户名获取用户详情
    """
    result = await db.execute(
        select(UserModel).where(UserModel.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    注册新用户
    """
    # 检查用户名是否已存在
    result = await db.execute(
        select(UserModel).where(UserModel.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    result = await db.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建用户（密码需要加密）
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = UserModel(
        username=user_data.username,
        email=user_data.email,
        hashed_password=pwd_context.hash(user_data.password),
        display_name=user_data.display_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
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
    
    await db.delete(user)
    await db.commit()
    
    return MessageResponse(message="用户已删除")


# TODO: 添加登录/认证相关接口
# @router.post("/auth/login")
# async def login(...)
# 
# @router.post("/auth/refresh")
# async def refresh_token(...)
