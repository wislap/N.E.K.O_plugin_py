from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.category import Category
from app.services.category_service import CategoryService

router = APIRouter()


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
