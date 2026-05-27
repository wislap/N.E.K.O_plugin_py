import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ServerKeyPair
from app.services.signature_service import SignatureService
from tests.conftest import create_test_user


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "Str0ngPass!42") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def create_plugin(client: AsyncClient, owner_token: str, admin_token: str, slug: str = "plugin-permissions") -> dict:
    repo_slug = slug.replace("-", "_")
    draft_response = await client.post(
        "/api/v1/review/submissions/drafts",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "repo_url": f"https://github.com/neko/n.e.k.o_plugin_{repo_slug}",
            "plugin_name": "Plugin Permissions",
            "plugin_slug": repo_slug,
            "description": "Permission checks",
            "short_description": "Permission checks",
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()

    submit_response = await client.post(
        f"/api/v1/review/submissions/{draft['id']}/submit",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert submit_response.status_code == 200

    start_response = await client.post(
        f"/api/v1/admin/review/submissions/{draft['id']}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert start_response.status_code == 200
    case_id = start_response.json()["current_review_case_id"]

    approve_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"summary": "Ready", "force": True},
    )
    assert approve_response.status_code == 200
    plugin_id = approve_response.json()["plugin_id"]
    plugin_response = await client.get(f"/api/v1/plugins/{plugin_id}")
    assert plugin_response.status_code == 200
    return plugin_response.json()


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
    plugin = await create_plugin(client, owner_token, admin_token)

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
        "/api/v1/admin/signatures/keys",
        json={"name": "release-key", "set_as_default": True},
    )
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"name": "release-key", "set_as_default": True},
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "release-key", "set_as_default": True},
    )
    assert admin_create.status_code == 201
    keypair_id = admin_create.json()["id"]

    public_keys = await client.get("/api/v1/signatures/public-keys")
    assert public_keys.status_code == 200
    assert len(public_keys.json()) == 1

    member_list = await client.get(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 403

    admin_deactivate = await client.post(
        f"/api/v1/admin/signatures/keys/{keypair_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_deactivate.status_code == 200


async def test_default_keypair_switch_rolls_back_when_insert_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await create_test_user(db_session, "signature_atomic_admin", "signature-atomic-admin@example.com", is_admin=True)
    admin_token = await login(client, "signature_atomic_admin")

    initial_response = await client.post(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "stable-default", "set_as_default": True},
    )
    assert initial_response.status_code == 201
    initial_keypair_id = initial_response.json()["id"]

    def fail_add_keypair(*args, **kwargs):
        raise RuntimeError("key insert boom")

    monkeypatch.setattr(SignatureService, "_add_keypair", fail_add_keypair)

    with pytest.raises(RuntimeError, match="key insert boom"):
        await client.post(
            "/api/v1/admin/signatures/keys",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "broken-default", "set_as_default": True},
        )

    initial_keypair = await db_session.get(ServerKeyPair, initial_keypair_id)
    assert initial_keypair is not None
    assert initial_keypair.is_default is True
    assert await db_session.scalar(
        select(ServerKeyPair.id).where(ServerKeyPair.name == "broken-default")
    ) is None
