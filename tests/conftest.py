import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, get_db
from app.main import app
from app.models import User
from app.models.permission import Permission, PermissionGroup, permission_group_items, user_permission_groups
from app.core.security import get_password_hash


@pytest_asyncio.fixture()
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def create_test_user(
    db: AsyncSession,
    username: str = "admin",
    email: str = "admin@example.com",
    password: str = "password123",
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def grant_permission(db: AsyncSession, user: User, permission_code: str) -> None:
    result = await db.execute(
        select(Permission).where(Permission.code == permission_code)
    )
    permission = result.scalar_one_or_none()
    if permission is None:
        permission = Permission(
            code=permission_code,
            name=permission_code,
            category=permission_code.split(":", 1)[0],
            is_active=True,
        )
        db.add(permission)
        await db.flush()

    group = PermissionGroup(
        code=f"test_{permission_code.replace(':', '_')}_{user.id}",
        name=f"test {permission_code}",
        group_type="custom",
        is_active=True,
        is_system=False,
    )
    db.add(group)
    await db.flush()
    await db.execute(
        permission_group_items.insert().values(
            group_id=group.id,
            permission_id=permission.id,
        )
    )
    await db.execute(
        user_permission_groups.insert().values(
            user_id=user.id,
            group_id=group.id,
        )
    )
    await db.commit()
