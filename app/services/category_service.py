from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    
    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
        """通过ID获取分类"""
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_category_by_slug(db: AsyncSession, slug: str) -> Optional[Category]:
        """通过slug获取分类"""
        result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_categories(db: AsyncSession) -> List[Category]:
        """获取所有分类"""
        result = await db.execute(
            select(Category).order_by(Category.sort_order, Category.name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_categories_with_count(db: AsyncSession) -> List[Category]:
        """获取所有分类及其插件数量"""
        from app.models.plugin import Plugin, PluginStatus
        from app.models.plugin_category import PluginCategory
        
        result = await db.execute(
            select(
                Category,
                func.count(PluginCategory.plugin_id).label('plugin_count')
            )
            .outerjoin(
                PluginCategory,
                Category.id == PluginCategory.category_id
            )
            .outerjoin(
                Plugin,
                and_(
                    PluginCategory.plugin_id == Plugin.id,
                    Plugin.status == PluginStatus.APPROVED
                )
            )
            .group_by(Category.id)
            .order_by(Category.sort_order, Category.name)
        )
        
        categories = []
        for category, count in result.all():
            category.plugin_count = count
            categories.append(category)
        
        return categories
    
    @staticmethod
    async def create_category(db: AsyncSession, category_data: CategoryCreate) -> Category:
        """创建新分类"""
        # 检查slug是否已存在
        existing = await CategoryService.get_category_by_slug(db, category_data.slug)
        if existing:
            raise ValueError(f"分类slug '{category_data.slug}' 已存在")
        
        category = Category(
            name=category_data.name,
            slug=category_data.slug,
            description=category_data.description,
            icon=category_data.icon,
            sort_order=category_data.sort_order
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    
    @staticmethod
    async def update_category(
        db: AsyncSession,
        category: Category,
        update_data: CategoryUpdate
    ) -> Category:
        """更新分类"""
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(category, field, value)
        
        await db.commit()
        await db.refresh(category)
        return category
    
    @staticmethod
    async def delete_category(db: AsyncSession, category: Category) -> None:
        """删除分类"""
        await db.delete(category)
        await db.commit()
