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


async def create_plugin(client: AsyncClient, token: str, slug: str = "owned-plugin") -> dict:
    response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Owned Plugin",
            "slug": slug,
            "description": "Plugin for permission tests",
            "short_description": "Permission tests",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_reviews_require_login_and_owner_for_mutations(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "owner", "review-owner@example.com")
    await create_test_user(db_session, "reviewer", "reviewer@example.com")
    await create_test_user(db_session, "other", "review-other@example.com")
    await create_test_user(db_session, "admin", "review-admin@example.com", is_admin=True)

    owner_token = await login(client, "owner")
    reviewer_token = await login(client, "reviewer")
    other_token = await login(client, "other")
    admin_token = await login(client, "admin")
    plugin = await create_plugin(client, owner_token, "review-target")

    anonymous_create = await client.post(
        f"/api/v1/plugins/{plugin['id']}/reviews",
        json={"rating": 4.5, "title": "Nice"},
    )
    assert anonymous_create.status_code in {401, 403}

    create_response = await client.post(
        f"/api/v1/plugins/{plugin['id']}/reviews",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"rating": 4.5, "title": "Nice", "content": "Works well"},
    )
    assert create_response.status_code == 201
    review = create_response.json()
    assert review["author_id"] != 1

    other_update = await client.put(
        f"/api/v1/reviews/{review['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"rating": 2, "title": "Changed"},
    )
    assert other_update.status_code == 403

    owner_update = await client.put(
        f"/api/v1/reviews/{review['id']}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"rating": 5, "title": "Still nice"},
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["rating"] == 5

    other_delete = await client.delete(
        f"/api/v1/reviews/{review['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_delete.status_code == 403

    admin_delete = await client.delete(
        f"/api/v1/reviews/{review['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200


async def test_versions_require_plugin_owner_or_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "owner", "version-owner@example.com")
    await create_test_user(db_session, "other", "version-other@example.com")
    await create_test_user(db_session, "admin", "version-admin@example.com", is_admin=True)

    owner_token = await login(client, "owner")
    other_token = await login(client, "other")
    admin_token = await login(client, "admin")
    plugin = await create_plugin(client, owner_token, "version-target")

    payload = {
        "version": "1.1.0",
        "changelog": "Initial release",
        "download_url": "https://example.com/plugin.zip",
    }

    anonymous_create = await client.post(
        f"/api/v1/plugins/{plugin['id']}/versions",
        json=payload,
    )
    assert anonymous_create.status_code in {401, 403}

    other_create = await client.post(
        f"/api/v1/plugins/{plugin['id']}/versions",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    assert other_create.status_code == 403

    owner_create = await client.post(
        f"/api/v1/plugins/{plugin['id']}/versions",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert owner_create.status_code == 201
    version = owner_create.json()

    other_delete = await client.delete(
        f"/api/v1/plugins/{plugin['id']}/versions/{version['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_delete.status_code == 403

    admin_delete = await client.delete(
        f"/api/v1/plugins/{plugin['id']}/versions/{version['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200
