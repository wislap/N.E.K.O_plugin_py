"""publish-from-release 错误码与成功路径覆盖矩阵（spec R3 / R9）。"""

from __future__ import annotations

import io
import zipfile

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Version
from sqlalchemy import select

from tests.conftest import (
    build_zip_with_metadata,
    create_test_user,
    login,
)

pytestmark = pytest.mark.asyncio


async def test_publish_from_release_success(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """作者发版成功 → 201 + 正确字段（含 sha256 由后端字节级计算）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(
        author=author, repo_url="https://github.com/alice/myplugin"
    )
    token = await login(client, "alice")

    asset_bytes = build_zip_with_metadata(b"x" * 32, payload_hash="a" * 64)
    release_url, expected_sha = mock_github_release(
        asset_bytes=asset_bytes, tag="v1.0.0", owner="alice", repo="myplugin"
    )

    resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url, "channel": "stable", "changelog": "hi"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == "1.0.0"
    assert body["channel"] == "stable"
    assert body["is_latest"] is True
    assert body["yanked_at"] is None
    assert body["package_sha256"] == expected_sha
    assert body["package_url"].endswith("pkg.neko-plugin")
    assert body["payload_hash"] == "a" * 64
    assert body["release_tag"] == "1.0.0"  # 后端去前导 v
    assert body["verification_status"] == "passed"


async def test_publish_from_release_forbidden_for_non_author(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """非作者非 admin → 403 forbidden。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    await create_test_user(db_session, "bob", "bob@example.com")
    plugin = await make_plugin(author=author)
    bob_token = await login(client, "bob")

    asset_bytes = build_zip_with_metadata(b"x")
    release_url, _ = mock_github_release(
        asset_bytes=asset_bytes, tag="v1.0.0", owner="alice", repo="myplugin"
    )

    resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"release_url": release_url},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


async def test_publish_from_release_repo_mismatch(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """release owner/repo 与 plugin.repo_url 不一致 → 400 release_repo_mismatch。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    asset_bytes = build_zip_with_metadata(b"x")
    release_url, _ = mock_github_release(
        asset_bytes=asset_bytes, tag="v1.0.0", owner="other", repo="otherrepo"
    )

    resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "release_repo_mismatch"


async def test_publish_from_release_invalid_channel(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    """非法 channel → 400 invalid_channel（请求被 Pydantic Literal 校验或 service）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author)
    token = await login(client, "alice")

    resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": "https://github.com/alice/myplugin/releases/tag/v1.0.0", "channel": "nightly"},
    )
    # Pydantic Literal["stable","beta"] 会先抛 422；如果未来放宽 schema
    # 走 service 校验则 400 invalid_channel。两者都接受。
    assert resp.status_code in (400, 422)
    if resp.status_code == 400:
        assert resp.json()["code"] == "invalid_channel"


async def test_publish_from_release_asset_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    """release 中无 .neko-plugin / .neko-bundle → 400 release_asset_not_found。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    with respx.mock(assert_all_called=False) as router:
        router.get(
            "https://api.github.com/repos/alice/myplugin/releases/tags/v1.0.0"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "tag_name": "v1.0.0",
                    "html_url": "https://github.com/alice/myplugin/releases/tag/v1.0.0",
                    "target_commitish": "0" * 40,
                    "assets": [
                        {
                            "name": "source.tar.gz",
                            "browser_download_url": "https://example.com/source.tar.gz",
                            "size": 100,
                        }
                    ],
                },
            )
        )

        resp = await client.post(
            f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "release_url": "https://github.com/alice/myplugin/releases/tag/v1.0.0",
            },
        )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "release_asset_not_found"


async def test_publish_from_release_version_already_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """同 (plugin, version) 二次发版 → 409 version_already_exists。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    asset_bytes = build_zip_with_metadata(b"x")
    release_url, _ = mock_github_release(
        asset_bytes=asset_bytes, tag="v1.0.0", owner="alice", repo="myplugin"
    )

    first = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url},
    )
    assert first.status_code == 201, first.text

    # 重发同 release_url —— 同 release_url 被同 mock 二次注册才能 fire；
    # 这里直接复用，respx mock 仍然有效（同一 fixture context 内）。
    second = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "version_already_exists"


async def test_publish_from_release_publish_failed_on_github_5xx(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    """GitHub 持续返回 5xx → 502 release_publish_failed（重试 1 次后仍失败）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    with respx.mock(assert_all_called=False) as router:
        router.get(
            "https://api.github.com/repos/alice/myplugin/releases/tags/v1.0.0"
        ).mock(return_value=httpx.Response(503))

        resp = await client.post(
            f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "release_url": "https://github.com/alice/myplugin/releases/tag/v1.0.0",
            },
        )
    assert resp.status_code == 502
    assert resp.json()["code"] == "release_publish_failed"


async def test_publish_from_release_switches_is_latest(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """连发两个 stable 版本，旧的 is_latest 自动置 false（spec R3.13 / Property P1）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    # v1.0.0
    a_bytes = build_zip_with_metadata(b"v1")
    url_a, _ = mock_github_release(
        asset_bytes=a_bytes, tag="v1.0.0", owner="alice", repo="myplugin"
    )
    r1 = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": url_a},
    )
    assert r1.status_code == 201

    # v1.1.0
    b_bytes = build_zip_with_metadata(b"v2")
    url_b, _ = mock_github_release(
        asset_bytes=b_bytes, tag="v1.1.0", owner="alice", repo="myplugin"
    )
    r2 = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": url_b},
    )
    assert r2.status_code == 201

    # 同 (plugin, channel='stable') 满足 is_latest=true AND yanked_at IS NULL
    # 的版本应当恰好为 1，且就是 v1.1.0
    rows = (
        await db_session.execute(
            select(Version).where(
                Version.plugin_id == plugin.id,
                Version.channel == "stable",
                Version.is_latest.is_(True),
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].version == "1.1.0"
