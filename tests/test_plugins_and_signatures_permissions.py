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


async def create_plugin(client: AsyncClient, token: str, slug: str = "plugin-permissions") -> dict:
    response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Plugin Permissions",
            "slug": slug,
            "description": "Permission checks",
            "short_description": "Permission checks",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_plugin_update_delete_require_owner_or_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "owner", "plugin-owner@example.com")
    await create_test_user(db_session, "other", "plugin-other@example.com")
    await create_test_user(db_session, "admin", "plugin-admin@example.com", is_admin=True)

    owner_token = await login(client, "owner")
    other_token = await login(client, "other")
    admin_token = await login(client, "admin")
    plugin = await create_plugin(client, owner_token)

    other_update = await client.put(
        f"/api/v1/plugins/{plugin['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"name": "Taken over"},
    )
    assert other_update.status_code == 403

    owner_update = await client.put(
        f"/api/v1/plugins/{plugin['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Owner renamed"},
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["name"] == "Owner renamed"

    other_delete = await client.delete(
        f"/api/v1/plugins/{plugin['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_delete.status_code == 403

    admin_delete = await client.delete(
        f"/api/v1/plugins/{plugin['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200


async def test_signature_key_management_requires_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "member", "signature-member@example.com")
    await create_test_user(db_session, "admin", "signature-admin@example.com", is_admin=True)

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")

    anonymous_create = await client.post(
        "/api/v1/signatures/admin/keys",
        params={"name": "release-key", "set_as_default": True},
    )
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/signatures/admin/keys",
        headers={"Authorization": f"Bearer {member_token}"},
        params={"name": "release-key", "set_as_default": True},
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/signatures/admin/keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"name": "release-key", "set_as_default": True},
    )
    assert admin_create.status_code == 201
    keypair_id = admin_create.json()["id"]

    public_keys = await client.get("/api/v1/signatures/public-keys")
    assert public_keys.status_code == 200
    assert len(public_keys.json()) == 1

    member_list = await client.get(
        "/api/v1/signatures/admin/keys",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 403

    admin_deactivate = await client.post(
        f"/api/v1/signatures/admin/keys/{keypair_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_deactivate.status_code == 200
