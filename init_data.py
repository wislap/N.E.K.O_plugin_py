"""
初始化数据脚本
用于创建默认的区域/分区
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.zone import Zone


async def init_zones():
    """初始化区域数据"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有数据
        from sqlalchemy import select
        result = await db.execute(select(Zone))
        existing = result.scalars().first()
        
        if existing:
            print("区域数据已存在，跳过初始化")
            return
        
        # 创建默认区域
        zones = [
            {
                "name": "游戏区",
                "slug": "game",
                "description": "游戏辅助、数据查询、攻略工具",
                "icon": "Gamepad2",
                "color": "#EF4444",
                "sort_order": 1
            },
            {
                "name": "陪玩区",
                "slug": "companion",
                "description": "陪玩匹配、语音互动、社交工具",
                "icon": "Heart",
                "color": "#EC4899",
                "sort_order": 2
            },
            {
                "name": "功能区",
                "slug": "function",
                "description": "实用工具、效率提升、系统增强",
                "icon": "Settings",
                "color": "#3B82F6",
                "sort_order": 3
            },
            {
                "name": "娱乐区",
                "slug": "entertainment",
                "description": "趣味插件、休闲娱乐、互动玩法",
                "icon": "Sparkles",
                "color": "#8B5CF6",
                "sort_order": 4
            },
            {
                "name": "工具区",
                "slug": "tool",
                "description": "开发工具、调试助手、管理工具",
                "icon": "Wrench",
                "color": "#10B981",
                "sort_order": 5
            }
        ]
        
        for zone_data in zones:
            zone = Zone(**zone_data)
            db.add(zone)
        
        await db.commit()
        print(f"已创建 {len(zones)} 个默认区域")


async def main():
    """主函数"""
    print("开始初始化数据...")
    
    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 初始化区域
    await init_zones()
    
    print("初始化完成！")
    
    # 关闭连接
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
