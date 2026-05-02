from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.models.review import Review
from app.models.plugin import Plugin
from app.services.plugin_service import PluginService
from app.services.notification_service import NotificationService


class ReviewService:
    
    @staticmethod
    async def get_review_by_id(db: AsyncSession, review_id: int) -> Optional[Review]:
        """通过ID获取评论"""
        result = await db.execute(
            select(Review)
            .options(selectinload(Review.author))
            .where(Review.id == review_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_plugin_reviews(
        db: AsyncSession,
        plugin_id: int,
        page: int = 1,
        page_size: int = 20
    ):
        """获取插件的评论列表"""
        query = (
            select(Review)
            .options(selectinload(Review.author))
            .where(Review.plugin_id == plugin_id)
        )
        
        # 获取总数
        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # 分页
        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(Review.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        reviews = result.scalars().all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "items": list(reviews),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    
    @staticmethod
    async def get_user_review_for_plugin(
        db: AsyncSession,
        plugin_id: int,
        user_id: int
    ) -> Optional[Review]:
        """获取用户对插件的评论"""
        result = await db.execute(
            select(Review).where(
                and_(Review.plugin_id == plugin_id, Review.author_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_review(
        db: AsyncSession,
        plugin_id: int,
        author_id: int,
        rating: float,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> Review:
        """创建评论"""
        # 检查用户是否已经评论过
        existing = await ReviewService.get_user_review_for_plugin(
            db, plugin_id, author_id
        )
        if existing:
            raise ValueError("您已经对该插件进行过评分")
        
        review = Review(
            plugin_id=plugin_id,
            author_id=author_id,
            rating=rating,
            title=title,
            content=content
        )
        
        db.add(review)
        plugin = await db.get(Plugin, plugin_id)
        if plugin and plugin.author_id != author_id:
            NotificationService.add(
                db,
                user_id=plugin.author_id,
                type="plugin_reviewed",
                title="插件收到新评论",
                content=f"你的插件「{plugin.name}」收到了一条 {rating:g} 分评论。",
                target_url=f"/plugin/{plugin.id}",
            )
        await db.commit()
        await db.refresh(review)
        
        # 更新插件评分
        await PluginService.update_rating(db, plugin_id)
        
        refreshed = await ReviewService.get_review_by_id(db, review.id)
        return refreshed or review
    
    @staticmethod
    async def update_review(
        db: AsyncSession,
        review: Review,
        rating: Optional[float] = None,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> Review:
        """更新评论"""
        if rating is not None:
            review.rating = rating
        if title is not None:
            review.title = title
        if content is not None:
            review.content = content
        
        await db.commit()
        await db.refresh(review)
        
        # 更新插件评分
        await PluginService.update_rating(db, review.plugin_id)
        
        refreshed = await ReviewService.get_review_by_id(db, review.id)
        return refreshed or review
    
    @staticmethod
    async def delete_review(db: AsyncSession, review: Review) -> None:
        """删除评论"""
        plugin_id = review.plugin_id
        await db.delete(review)
        await db.commit()
        
        # 更新插件评分
        await PluginService.update_rating(db, plugin_id)
    
    @staticmethod
    async def get_rating_distribution(db: AsyncSession, plugin_id: int) -> dict:
        """获取评分分布"""
        result = await db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.plugin_id == plugin_id)
            .group_by(Review.rating)
        )
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating, count in result.all():
            distribution[int(rating)] = count
        
        return distribution
