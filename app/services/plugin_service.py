from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime

from app.models.plugin import Plugin, PluginStatus
from app.models.category import Category
from app.core.time import utc_now
from app.schemas.plugin import PluginCreate, PluginUpdate, PluginSearchParams
from app.schemas.common import PaginatedResponse
from app.utils.plugin_validator import validate_plugin_repo


class PluginService:
    
    @staticmethod
    async def get_plugin_by_id(db: AsyncSession, plugin_id: int) -> Optional[Plugin]:
        """通过ID获取插件"""
        result = await db.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.categories),
                selectinload(Plugin.author),
                selectinload(Plugin.zone),
                selectinload(Plugin.reviews_history),
            )
            .where(Plugin.id == plugin_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_plugin_by_slug(db: AsyncSession, slug: str) -> Optional[Plugin]:
        """通过slug获取插件"""
        result = await db.execute(
            select(Plugin)
            .options(selectinload(Plugin.zone), selectinload(Plugin.reviews_history))
            .where(Plugin.slug == slug)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_plugins(
        db: AsyncSession,
        params: PluginSearchParams,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse:
        """获取插件列表（支持搜索和筛选）"""
        query = select(Plugin).options(
            selectinload(Plugin.categories),
            selectinload(Plugin.zone),
            selectinload(Plugin.reviews_history),
        )
        
        # 构建过滤条件
        filters = []
        
        # 状态过滤 - 默认只显示已通过的
        if params.status:
            filters.append(Plugin.status == params.status)
        else:
            filters.append(Plugin.status == PluginStatus.APPROVED)
        
        # 关键词搜索
        if params.q:
            search_filter = or_(
                Plugin.name.ilike(f"%{params.q}%"),
                Plugin.description.ilike(f"%{params.q}%"),
                Plugin.short_description.ilike(f"%{params.q}%")
            )
            filters.append(search_filter)
        
        # 作者筛选
        if params.author:
            filters.append(Plugin.author_name == params.author)
        
        # 推荐插件筛选
        if params.featured_only:
            filters.append(Plugin.is_featured > 0)
        
        # 应用过滤条件
        if filters:
            query = query.where(and_(*filters))
        
        # 分类筛选（需要join）
        if params.category:
            query = query.join(Plugin.categories).where(Category.slug == params.category)
        
        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 排序
        sort_field = getattr(Plugin, params.sort_by or "created_at")
        if params.sort_order == "asc":
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))
        
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        plugins = result.scalars().all()
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            items=list(plugins),
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )

    @staticmethod
    async def get_plugins_by_author(
        db: AsyncSession,
        author_id: int
    ) -> List[Plugin]:
        """获取指定作者的所有插件"""
        result = await db.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.categories),
                selectinload(Plugin.zone),
                selectinload(Plugin.reviews_history),
            )
            .where(Plugin.author_id == author_id)
            .order_by(desc(Plugin.created_at))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def create_plugin(
        db: AsyncSession,
        plugin_data: PluginCreate,
        author_id: int,
        author_name: str
    ) -> Plugin:
        """创建新插件"""
        # 检查slug是否已存在
        existing = await PluginService.get_plugin_by_slug(db, plugin_data.slug)
        if existing:
            raise ValueError(f"插件slug '{plugin_data.slug}' 已存在")
        
        # 验证仓库命名规范
        if plugin_data.repo_url:
            is_valid, error_msg = validate_plugin_repo(plugin_data.repo_url)
            if not is_valid:
                raise ValueError(f"仓库地址验证失败: {error_msg}")
        
        zone_id = plugin_data.zone_id
        if plugin_data.zone_slug:
            from app.services.zone_service import ZoneService

            zone = await ZoneService.get_zone_by_slug(db, plugin_data.zone_slug)
            if not zone:
                raise ValueError(f"分区 '{plugin_data.zone_slug}' 不存在")
            zone_id = zone.id

        plugin = Plugin(
            name=plugin_data.name,
            slug=plugin_data.slug,
            description=plugin_data.description,
            short_description=plugin_data.short_description,
            author_id=author_id,
            author_name=author_name,
            download_url=plugin_data.download_url,
            icon_url=plugin_data.icon_url,
            repo_url=plugin_data.repo_url,
            readme=plugin_data.readme,
            zone_id=zone_id,
            tags=plugin_data.tags,
            status=PluginStatus.PENDING  # 新插件默认待审核
        )
        
        db.add(plugin)
        await db.flush()  # 获取plugin.id
        
        # 添加分类关联
        if plugin_data.category_ids:
            categories_result = await db.execute(
                select(Category).where(Category.id.in_(plugin_data.category_ids))
            )
            categories = categories_result.scalars().all()
            plugin.categories = list(categories)
        
        await db.commit()
        await db.refresh(plugin)
        return plugin
    
    @staticmethod
    async def update_plugin(
        db: AsyncSession,
        plugin: Plugin,
        update_data: PluginUpdate
    ) -> Plugin:
        """更新插件"""
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # 处理分类更新
        category_ids = update_dict.pop('category_ids', None)
        zone_slug = update_dict.pop('zone_slug', None)
        if category_ids is not None:
            categories_result = await db.execute(
                select(Category).where(Category.id.in_(category_ids))
            )
            categories = categories_result.scalars().all()
            plugin.categories = list(categories)

        if zone_slug is not None:
            from app.services.zone_service import ZoneService

            zone = await ZoneService.get_zone_by_slug(db, zone_slug)
            if not zone:
                raise ValueError(f"分区 '{zone_slug}' 不存在")
            plugin.zone_id = zone.id
        
        # 更新其他字段
        for field, value in update_dict.items():
            setattr(plugin, field, value)
        
        plugin.updated_at = utc_now()
        await db.commit()
        await db.refresh(plugin)
        return plugin
    
    @staticmethod
    async def delete_plugin(db: AsyncSession, plugin: Plugin) -> None:
        """删除插件"""
        await db.delete(plugin)
        await db.commit()
    
    @staticmethod
    async def approve_plugin(db: AsyncSession, plugin: Plugin) -> Plugin:
        """审核通过插件"""
        plugin.status = PluginStatus.APPROVED
        plugin.published_at = utc_now()
        await db.commit()
        await db.refresh(plugin)
        return plugin
    
    @staticmethod
    async def reject_plugin(db: AsyncSession, plugin: Plugin) -> Plugin:
        """拒绝插件"""
        plugin.status = PluginStatus.REJECTED
        await db.commit()
        await db.refresh(plugin)
        return plugin
    
    @staticmethod
    async def increment_download_count(db: AsyncSession, plugin_id: int) -> None:
        """增加下载计数"""
        plugin = await PluginService.get_plugin_by_id(db, plugin_id)
        if plugin:
            plugin.download_count += 1
            await db.commit()
    
    @staticmethod
    async def update_rating(db: AsyncSession, plugin_id: int) -> None:
        """更新插件评分"""
        from app.models.review import Review
        
        result = await db.execute(
            select(func.avg(Review.rating), func.count(Review.id))
            .where(Review.plugin_id == plugin_id)
        )
        avg_rating, count = result.one()
        
        plugin = await PluginService.get_plugin_by_id(db, plugin_id)
        if plugin:
            plugin.rating_average = round(avg_rating, 2) if avg_rating else 0.0
            plugin.rating_count = count
            await db.commit()
    
    @staticmethod
    async def get_featured_plugins(db: AsyncSession, limit: int = 10) -> List[Plugin]:
        """获取推荐插件"""
        result = await db.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.categories),
                selectinload(Plugin.zone),
                selectinload(Plugin.reviews_history),
            )
            .where(
                and_(
                    Plugin.is_featured > 0,
                    Plugin.status == PluginStatus.APPROVED
                )
            )
            .order_by(desc(Plugin.is_featured), desc(Plugin.download_count))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_popular_plugins(db: AsyncSession, limit: int = 10) -> List[Plugin]:
        """获取热门插件"""
        result = await db.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.categories),
                selectinload(Plugin.zone),
                selectinload(Plugin.reviews_history),
            )
            .where(Plugin.status == PluginStatus.APPROVED)
            .order_by(desc(Plugin.download_count))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_newest_plugins(db: AsyncSession, limit: int = 10) -> List[Plugin]:
        """获取最新插件"""
        result = await db.execute(
            select(Plugin)
            .options(
                selectinload(Plugin.categories),
                selectinload(Plugin.zone),
                selectinload(Plugin.reviews_history),
            )
            .where(Plugin.status == PluginStatus.APPROVED)
            .order_by(desc(Plugin.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
