from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker
from app.models.user import User
from app.schemas.category import Category, CategoryCreate, CategoryUpdate
from app.schemas.common import MessageResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["admin-categories"])
require_category_management = PermissionChecker("plugin:category")


@router.get("", response_model=List[Category])
async def list_categories(
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db),
):
    return await CategoryService.get_categories_with_count(db)


@router.post("", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CategoryService.create_category(db, category_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{category_id}", response_model=Category)
async def update_category(
    category_id: int,
    update_data: CategoryUpdate,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db),
):
    category = await CategoryService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    return await CategoryService.update_category(db, category, update_data)


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_category_management),
    db: AsyncSession = Depends(get_db),
):
    category = await CategoryService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    await CategoryService.delete_category(db, category)
    return MessageResponse(message="分类已删除")
