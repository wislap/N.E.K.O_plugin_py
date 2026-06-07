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
os.environ.setdefault("EMAIL_DELIVERY_MODE", "log")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, get_db
from app.main import app
from app.models import User
from app.core.security import get_password_hash
from app.core.time import utc_now
from app.services.permission_service import PermissionService


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
    password: str = "Str0ngPass!42",
    is_admin: bool = False,
    email_verified: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
        is_active=True,
        email_verified_at=utc_now() if email_verified else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def grant_permission(
    db: AsyncSession,
    user: User,
    permission_code: str,
    *,
    level: int = 100,
) -> None:
    service = PermissionService()
    await service.grant_permissions_system(
        db,
        user,
        [permission_code],
        level=level,
        code=f"test_{permission_code.replace(':', '_')}_{user.id}",
        name=f"test {permission_code}",
    )



# ─── 版本管理特性共享 fixture（被 tests/integration/ 与 tests/properties/ 共用） ─

import hashlib
import io
import zipfile
from typing import Any

import httpx
import pytest
import respx

from app.models import Plugin
from app.models.plugin import PluginStatus


def build_zip_with_metadata(
    payload: bytes = b"hello",
    *,
    payload_hash: str | None = None,
    asset_filename: str = "plugin.bin",
) -> bytes:
    """构造一个最小合法的 .neko-plugin ZIP 字节流。

    payload_hash 决定 metadata.toml 中 [payload].hash 的值；为 None 时省略
    该字段（用于测试 payload_hash 缺失的鲁棒路径，对应 spec R3.9）。
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if payload_hash is not None:
            metadata = (
                "[payload]\n"
                f'hash = "{payload_hash}"\n'
                'hash_algorithm = "sha256"\n'
            )
        else:
            metadata = "# no payload section\n"
        zf.writestr("metadata.toml", metadata)
        zf.writestr(f"payload/{asset_filename}", payload)
    return buf.getvalue()



@pytest.fixture
def mock_github_release():
    """工厂 fixture：注册 mock release 元数据 + asset 下载。

    用法：
        url, sha = mock_github_release(
            asset_bytes=zip_bytes,
            tag="v1.0.0",
            owner="alice",
            repo="myplugin",
        )
    返回 (release_html_url, sha256_hex_lower)。
    """
    with respx.mock(assert_all_called=False) as router:
        def _factory(
            *,
            asset_bytes: bytes,
            tag: str,
            owner: str,
            repo: str,
            target_commitish: str = "0123456789abcdef0123456789abcdef01234567",
            asset_name: str = "pkg.neko-plugin",
        ) -> tuple[str, str]:
            html_url = f"https://github.com/{owner}/{repo}/releases/tag/{tag}"
            asset_url = (
                f"https://github.com/{owner}/{repo}/releases/download/{tag}/{asset_name}"
            )
            release_payload: dict[str, Any] = {
                "tag_name": tag,
                "html_url": html_url,
                "target_commitish": target_commitish,
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": asset_url,
                        "size": len(asset_bytes),
                    }
                ],
            }
            api_url = (
                f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
            )
            router.get(api_url).mock(
                return_value=httpx.Response(200, json=release_payload)
            )
            router.get(asset_url).mock(
                return_value=httpx.Response(
                    200,
                    content=asset_bytes,
                    headers={"Content-Type": "application/octet-stream"},
                )
            )
            return html_url, hashlib.sha256(asset_bytes).hexdigest()

        yield _factory



@pytest_asyncio.fixture
async def make_plugin(db_session: AsyncSession):
    """工厂 fixture：在 db_session 内插一条 APPROVED plugin。"""

    counter = {"i": 0}

    async def _factory(
        *,
        author: User,
        repo_url: str = "https://github.com/alice/myplugin",
        slug: str | None = None,
        name: str | None = None,
    ) -> Plugin:
        counter["i"] += 1
        idx = counter["i"]
        plugin = Plugin(
            name=name or f"plugin-{idx}",
            slug=slug or f"plugin-slug-{idx}",
            author_id=author.id,
            author_name=author.username,
            repo_url=repo_url,
            zone_id=None,
            tags=[],
            status=PluginStatus.APPROVED,
        )
        db_session.add(plugin)
        await db_session.commit()
        await db_session.refresh(plugin)
        return plugin

    return _factory


async def login(client, username: str, password: str = "Str0ngPass!42") -> str:
    """登录并返回 access_token。"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
