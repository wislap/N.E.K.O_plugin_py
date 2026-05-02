import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin, Review
from app.services.notification_service import NotificationService
from app.services.plugin_service import PluginService
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

    pending_create = await client.post(
        f"/api/v1/plugins/{plugin['id']}/reviews",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"rating": 4.5, "title": "Pending"},
    )
    assert pending_create.status_code == 404

    approve_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"comment": "发布后允许评论"},
    )
    assert approve_response.status_code == 200

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


async def test_review_create_rolls_back_when_notification_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await create_test_user(db_session, "atomic_review_owner", "atomic-review-owner@example.com")
    await create_test_user(db_session, "atomic_reviewer", "atomic-reviewer@example.com")
    await create_test_user(db_session, "atomic_review_admin", "atomic-review-admin@example.com", is_admin=True)

    owner_token = await login(client, "atomic_review_owner")
    reviewer_token = await login(client, "atomic_reviewer")
    admin_token = await login(client, "atomic_review_admin")
    plugin = await create_plugin(client, owner_token, "atomic-review-create")

    approve_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"comment": "允许评论"},
    )
    assert approve_response.status_code == 200

    def fail_add(*args, **kwargs):
        raise RuntimeError("notification boom")

    monkeypatch.setattr(NotificationService, "add", fail_add)

    with pytest.raises(RuntimeError, match="notification boom"):
        await client.post(
            f"/api/v1/plugins/{plugin['id']}/reviews",
            headers={"Authorization": f"Bearer {reviewer_token}"},
            json={"rating": 4, "title": "Should rollback"},
        )

    assert await db_session.scalar(
        select(Review.id).where(Review.plugin_id == plugin["id"])
    ) is None
    db_plugin = await db_session.get(Plugin, plugin["id"])
    assert db_plugin is not None
    assert db_plugin.rating_count == 0
    assert db_plugin.rating_average == 0


async def test_review_update_rolls_back_when_rating_refresh_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    await create_test_user(db_session, "atomic_update_owner", "atomic-update-owner@example.com")
    await create_test_user(db_session, "atomic_update_reviewer", "atomic-update-reviewer@example.com")
    await create_test_user(db_session, "atomic_update_admin", "atomic-update-admin@example.com", is_admin=True)

    owner_token = await login(client, "atomic_update_owner")
    reviewer_token = await login(client, "atomic_update_reviewer")
    admin_token = await login(client, "atomic_update_admin")
    plugin = await create_plugin(client, owner_token, "atomic-review-update")

    approve_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"comment": "允许评论"},
    )
    assert approve_response.status_code == 200

    create_response = await client.post(
        f"/api/v1/plugins/{plugin['id']}/reviews",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"rating": 3, "title": "Original"},
    )
    assert create_response.status_code == 201
    review = create_response.json()

    async def fail_update_rating(*args, **kwargs):
        raise RuntimeError("rating boom")

    monkeypatch.setattr(PluginService, "update_rating", fail_update_rating)

    with pytest.raises(RuntimeError, match="rating boom"):
        await client.put(
            f"/api/v1/reviews/{review['id']}",
            headers={"Authorization": f"Bearer {reviewer_token}"},
            json={"rating": 5, "title": "Should rollback"},
        )

    db_review = await db_session.get(Review, review["id"])
    assert db_review is not None
    assert db_review.rating == 3
    assert db_review.title == "Original"


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
