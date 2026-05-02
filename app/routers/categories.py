from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.user import User
from app.schemas.category import Category, CategoryCreate, CategoryUpdate
from app.schemas.common import MessageResponse
from app.services.category_service import CategoryService

router = APIRouter()
require_category_management = PermissionChecker("plugin:category")


@router.get("/categories", response_model=List[Category])
async def list_categories(
    with_count: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有分类列表
    """
    if with_count:
        categories = await CategoryService.get_categories_with_count(db)
    else:
        categories = await CategoryService.get_categories(db)
    return categories


@router.get("/categories/{category_id}", response_model=Category)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取分类详情
    """
    category = await CategoryService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    return category


@router.get("/categories/slug/{slug}", response_model=Category)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    通过slug获取分类详情
    """
    category = await CategoryService.get_category_by_slug(db, slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    return category


@router.post("/categories", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新分类（需要管理员权限）
    """
    try:
        category = await CategoryService.create_category(db, category_data)
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: int,
    update_data: CategoryUpdate,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db)
):
    """
    更新分类信息（需要管理员权限）
    """
    category = await CategoryService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    updated_category = await CategoryService.update_category(db, category, update_data)
    return updated_category


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db)
):
    """
    删除分类（需要管理员权限）
    """
    category = await CategoryService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分类不存在"
        )
    
    await CategoryService.delete_category(db, category)
    return MessageResponse(message="分类已删除")
