import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "password123") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_create_plugin_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/v1/plugins",
        json={
            "name": "Demo Plugin",
            "slug": "demo-plugin",
            "description": "A demo plugin",
        },
    )

    assert response.status_code in {401, 403}


async def test_plugin_create_approve_list_and_download(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(
        db_session,
        username="owner",
        email="owner@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="admin",
        email="admin@example.com",
        is_admin=True,
    )

    owner_token = await login(client, "owner")
    admin_token = await login(client, "admin")

    create_response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Demo Plugin",
            "slug": "demo-plugin",
            "description": "A demo plugin",
            "short_description": "Demo",
        },
    )

    assert create_response.status_code == 201
    plugin = create_response.json()
    assert plugin["status"] == "pending"

    my_plugins_response = await client.get(
        "/api/v1/plugins/mine",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert my_plugins_response.status_code == 200
    my_plugins = my_plugins_response.json()
    assert len(my_plugins) == 1
    assert my_plugins[0]["slug"] == "demo-plugin"

    pending_list = await client.get("/api/v1/plugins")
    assert pending_list.status_code == 200
    assert pending_list.json()["total"] == 0

    approve_response = await client.post(
        f"/api/v1/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    approved_list = await client.get("/api/v1/plugins")
    assert approved_list.status_code == 200
    assert approved_list.json()["total"] == 1
    assert approved_list.json()["items"][0]["slug"] == "demo-plugin"

    download_response = await client.post(f"/api/v1/plugins/{plugin['id']}/download")
    assert download_response.status_code == 200
    assert download_response.json()["success"] is True
