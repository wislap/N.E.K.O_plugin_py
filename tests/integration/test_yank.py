"""yank 错误码 + 自动晋级 + 通知写入覆盖矩阵（spec R4 / R5 / R9）。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Version

from tests.conftest import (
    build_zip_with_metadata,
    create_test_user,
    login,
)

pytestmark = pytest.mark.asyncio


async def _publish(
    client: AsyncClient,
    *,
    plugin_id: int,
    token: str,
    release_url: str,
    channel: str = "stable",
) -> dict:
    resp = await client.post(
        f"/api/v1/plugins/{plugin_id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url, "channel": channel},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_yank_already_yanked_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """重复 yank 同一版本 → 409 version_already_yanked。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    asset = build_zip_with_metadata(b"x")
    url, _ = mock_github_release(
        asset_bytes=asset, tag="v1.0.0", owner="alice", repo="myplugin"
    )
    v = await _publish(client, plugin_id=plugin.id, token=token, release_url=url)

    first = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v['id']}/yank",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "first yank"},
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v['id']}/yank",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "second yank"},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "version_already_yanked"


async def test_yank_latest_promotes_next_version(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """yank latest 后，列表查 latest 应该返回次新非 yanked 版本（spec R4.4 / Property P2）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    a, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"v1"), tag="v1.0.0", owner="alice", repo="myplugin"
    )
    b, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"v2"), tag="v1.1.0", owner="alice", repo="myplugin"
    )
    v1 = await _publish(client, plugin_id=plugin.id, token=token, release_url=a)
    v2 = await _publish(client, plugin_id=plugin.id, token=token, release_url=b)

    # v2 是当前 latest
    latest_before = await client.get(
        f"/api/v1/plugins/{plugin.id}/versions/latest"
    )
    assert latest_before.status_code == 200
    assert latest_before.json()["version"] == "1.1.0"

    yank_resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v2['id']}/yank",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "broken"},
    )
    assert yank_resp.status_code == 200, yank_resp.text
    body = yank_resp.json()
    assert body["yanked"]["yanked_at"] is not None
    assert body["promoted"] is not None
    assert body["promoted"]["version"] == "1.0.0"

    # latest 现在应该是 v1.0.0
    latest_after = await client.get(
        f"/api/v1/plugins/{plugin.id}/versions/latest"
    )
    assert latest_after.status_code == 200
    assert latest_after.json()["version"] == "1.0.0"
    # 而且 v1 是 is_latest=true
    rows = (
        await db_session.execute(
            select(Version).where(
                Version.plugin_id == plugin.id,
                Version.channel == "stable",
                Version.is_latest.is_(True),
                Version.yanked_at.is_(None),
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].version == "1.0.0"


async def test_yank_only_version_clears_latest(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """如果 channel 只有一条版本被 yank，latest 接口返回 404 latest_version_not_found。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    url, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"x"),
        tag="v1.0.0",
        owner="alice",
        repo="myplugin",
    )
    v = await _publish(client, plugin_id=plugin.id, token=token, release_url=url)

    yank_resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v['id']}/yank",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "only one"},
    )
    assert yank_resp.status_code == 200
    assert yank_resp.json()["promoted"] is None

    latest = await client.get(f"/api/v1/plugins/{plugin.id}/versions/latest")
    assert latest.status_code == 404
    assert latest.json()["code"] == "latest_version_not_found"


async def test_yank_writes_notification_for_author(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """yank latest 时给作者写一条 notification（spec R4.5）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    admin = await create_test_user(
        db_session, "boss", "boss@example.com", is_admin=True
    )
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    admin_token = await login(client, "boss")

    # 作者发版（用 alice token）
    alice_token = await login(client, "alice")
    url, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"x"),
        tag="v1.0.0",
        owner="alice",
        repo="myplugin",
    )
    v = await _publish(client, plugin_id=plugin.id, token=alice_token, release_url=url)

    # admin 撤回
    yank_resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v['id']}/yank",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "violates policy"},
    )
    assert yank_resp.status_code == 200, yank_resp.text

    # 作者收到一条 notification
    rows = (
        await db_session.execute(
            select(Notification).where(
                Notification.user_id == author.id,
                Notification.type == "version.yanked",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    note = rows[0]
    assert "1.0.0" in note.title
    # admin 操作时文案应包含"管理员"
    assert "管理员" in note.title
    assert note.content == "violates policy"


async def test_get_latest_404_when_no_versions(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    """没有任何版本时 latest 接口 404 + 错误码 latest_version_not_found。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author)

    resp = await client.get(f"/api/v1/plugins/{plugin.id}/versions/latest")
    assert resp.status_code == 404
    assert resp.json()["code"] == "latest_version_not_found"


async def test_list_versions_filters_by_channel_and_yanked(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """list 接口的 channel + include_yanked 过滤封闭性（spec R5）。"""
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(author=author, repo_url="https://github.com/alice/myplugin")
    token = await login(client, "alice")

    a, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"a"), tag="v1.0.0", owner="alice", repo="myplugin"
    )
    b, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"b"), tag="v1.1.0", owner="alice", repo="myplugin"
    )
    c, _ = mock_github_release(
        asset_bytes=build_zip_with_metadata(b"c"), tag="v0.9.0-beta", owner="alice", repo="myplugin"
    )

    await _publish(client, plugin_id=plugin.id, token=token, release_url=a, channel="stable")
    v_b = await _publish(client, plugin_id=plugin.id, token=token, release_url=b, channel="stable")
    v_c = await _publish(client, plugin_id=plugin.id, token=token, release_url=c, channel="beta")

    # yank v1.1.0 stable
    yank_resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/{v_b['id']}/yank",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "x"},
    )
    assert yank_resp.status_code == 200

    # 默认 list (include_yanked=false) → 不含 v1.1.0
    default_list = await client.get(f"/api/v1/plugins/{plugin.id}/versions")
    assert default_list.status_code == 200
    items = default_list.json()
    versions_in = {item["version"] for item in items}
    assert "1.1.0" not in versions_in
    assert "1.0.0" in versions_in
    assert "0.9.0-beta" in versions_in

    # include_yanked=true → 含 v1.1.0
    full_list = await client.get(
        f"/api/v1/plugins/{plugin.id}/versions?include_yanked=true"
    )
    assert full_list.status_code == 200
    items = full_list.json()
    versions_in = {item["version"] for item in items}
    assert "1.1.0" in versions_in

    # channel=beta → 仅 v_c
    beta_list = await client.get(f"/api/v1/plugins/{plugin.id}/versions?channel=beta")
    assert beta_list.status_code == 200
    items = beta_list.json()
    assert len(items) == 1
    assert items[0]["version"] == "0.9.0-beta"
    assert items[0]["channel"] == "beta"
    assert v_c["id"] == items[0]["id"]
