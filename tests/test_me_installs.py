import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import PluginStatus
from app.models.user_plugin_install import UserPluginInstall
from tests.conftest import create_test_user, login


pytestmark = pytest.mark.asyncio


async def test_record_my_install_creates_and_lists_record(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    user = await create_test_user(db_session, username="installer")
    plugin = await make_plugin(author=user, slug="hello-plugin")
    token = await login(client, "installer")

    response = await client.post(
        "/api/v1/me/installs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plugin_id": plugin.id,
            "version": "1.2.3",
            "channel": "stable",
            "package_sha256": "a" * 64,
            "payload_hash": "payload-hash",
            "installed_plugin_id": "hello-plugin",
            "client_id": "neko-web-bridge",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plugin_id"] == plugin.id
    assert body["version"] == "1.2.3"
    assert body["client_id"] == "neko-web-bridge"

    list_response = await client.get(
        "/api/v1/me/installs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert [item["plugin_id"] for item in list_response.json()] == [plugin.id]


async def test_record_my_install_upserts_existing_record(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    user = await create_test_user(db_session, username="upserter")
    plugin = await make_plugin(author=user)
    token = await login(client, "upserter")

    for version in ("1.0.0", "1.1.0"):
        response = await client.post(
            "/api/v1/me/installs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "plugin_id": plugin.id,
                "version": version,
                "package_sha256": "b" * 64,
            },
        )
        assert response.status_code == 201

    result = await db_session.execute(select(UserPluginInstall))
    records = list(result.scalars().all())
    assert len(records) == 1
    assert records[0].version == "1.1.0"


async def test_record_my_install_rejects_unpublished_plugin(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
):
    user = await create_test_user(db_session, username="blocked")
    plugin = await make_plugin(author=user)
    plugin.status = PluginStatus.DISABLED
    await db_session.commit()
    token = await login(client, "blocked")

    response = await client.post(
        "/api/v1/me/installs",
        headers={"Authorization": f"Bearer {token}"},
        json={"plugin_id": plugin.id, "version": "1.0.0"},
    )

    assert response.status_code == 404
