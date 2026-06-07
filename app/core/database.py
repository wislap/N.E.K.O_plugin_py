from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)


if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明基类
Base = declarative_base()


def _ensure_development_columns(sync_connection) -> None:
    """补齐开发库中 create_all 不会自动新增的已知列。"""
    inspector = inspect(sync_connection)
    if "permission_groups" not in inspector.get_table_names():
        return

    permission_group_columns = {
        column["name"] for column in inspector.get_columns("permission_groups")
    }
    if "level" not in permission_group_columns:
        sync_connection.execute(
            text(
                "ALTER TABLE permission_groups "
                "ADD COLUMN level INTEGER NOT NULL DEFAULT 10"
            )
        )
        sync_connection.execute(
            text("UPDATE permission_groups SET level = 1000 WHERE code = 'super_admin'")
        )
        sync_connection.execute(
            text("UPDATE permission_groups SET level = 300 WHERE code = 'system_admin'")
        )
        sync_connection.execute(
            text(
                "UPDATE permission_groups SET level = 200 "
                "WHERE code IN ('plugin_admin', 'ai_admin')"
            )
        )


async def ensure_development_schema() -> None:
    """开发环境自动建表，并补齐旧本地库缺失的轻量 schema 变更。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_development_columns)


async def get_db():
    """获取数据库会话的依赖函数"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
