from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.review import Review, ReviewCreate, ReviewUpdate
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.review_service import ReviewService
from app.services.plugin_service import PluginService

router = APIRouter()


@router.get("/plugins/{plugin_id}/reviews", response_model=PaginatedResponse[Review])
async def list_plugin_reviews(
    plugin_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件的评论列表
    """
    # 检查插件是否存在
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    result = await ReviewService.get_plugin_reviews(db, plugin_id, page, page_size)
    return PaginatedResponse(**result)


@router.get("/plugins/{plugin_id}/reviews/distribution")
async def get_rating_distribution(
    plugin_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取插件评分分布
    """
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    distribution = await ReviewService.get_rating_distribution(db, plugin_id)
    return {
        "distribution": distribution,
        "average": plugin.rating_average,
        "total": plugin.rating_count
    }


@router.post("/plugins/{plugin_id}/reviews", response_model=Review, status_code=status.HTTP_201_CREATED)
async def create_review(
    plugin_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    为插件创建评分和评论（需要登录，每个插件只能评分一次）
    """
    # 检查插件是否存在
    plugin = await PluginService.get_plugin_by_id(db, plugin_id)
    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="插件不存在"
        )
    
    try:
        # 临时使用固定用户ID
        review = await ReviewService.create_review(
            db,
            plugin_id=plugin_id,
            author_id=current_user.id,
            rating=review_data.rating,
            title=review_data.title,
            content=review_data.content
        )
        return review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/reviews/{review_id}", response_model=Review)
async def update_review(
    review_id: int,
    update_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新评论（需要评论作者权限）
    """
    review = await ReviewService.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    if review.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改此评论"
        )
    
    updated_review = await ReviewService.update_review(
        db,
        review,
        rating=update_data.rating,
        title=update_data.title,
        content=update_data.content
    )
    return updated_review


@router.delete("/reviews/{review_id}", response_model=MessageResponse)
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除评论（需要评论作者或管理员权限）
    """
    review = await ReviewService.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在"
        )
    
    if review.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除此评论"
        )
    
    await ReviewService.delete_review(db, review)
    return MessageResponse(message="评论已删除")
