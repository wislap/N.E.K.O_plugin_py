import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from tests.conftest import create_test_user, grant_permission


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

    admin_notifications = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_notifications.status_code == 200
    assert any(item["type"] == "plugin_submitted" for item in admin_notifications.json())

    pending_list = await client.get("/api/v1/plugins")
    assert pending_list.status_code == 200
    assert pending_list.json()["total"] == 0

    pending_detail = await client.get(f"/api/v1/plugins/{plugin['id']}")
    assert pending_detail.status_code == 404

    pending_download = await client.post(f"/api/v1/plugins/{plugin['id']}/download")
    assert pending_download.status_code == 404

    approve_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"comment": "资料完整，审核通过"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["review_summary"]["stage"] == "approved"
    assert approve_response.json()["review_summary"]["manual_review_notes"] == "资料完整，审核通过"

    owner_notifications = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_notifications.status_code == 200
    assert any(item["type"] == "plugin_approved" for item in owner_notifications.json())

    approved_detail = await client.get(f"/api/v1/plugins/{plugin['id']}")
    assert approved_detail.status_code == 200
    assert approved_detail.json()["slug"] == "demo-plugin"

    approved_list = await client.get("/api/v1/plugins")
    assert approved_list.status_code == 200
    assert approved_list.json()["total"] == 1
    assert approved_list.json()["items"][0]["slug"] == "demo-plugin"

    approved_status_list = await client.get("/api/v1/plugins?status=approved")
    assert approved_status_list.status_code == 200
    assert approved_status_list.json()["total"] == 1

    download_response = await client.post(f"/api/v1/plugins/{plugin['id']}/download")
    assert download_response.status_code == 200
    assert download_response.json()["success"] is True

    review_response = await client.post(
        f"/api/v1/plugins/{plugin['id']}/reviews",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"rating": 5, "title": "好用", "content": "闭环测试评论"},
    )
    assert review_response.status_code == 201
    assert review_response.json()["content"] == "闭环测试评论"

    reviews_response = await client.get(f"/api/v1/plugins/{plugin['id']}/reviews")
    assert reviews_response.status_code == 200
    assert reviews_response.json()["total"] == 1

    owner_notifications_after_review = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert any(
        item["type"] == "plugin_reviewed"
        for item in owner_notifications_after_review.json()
    )


async def test_admin_reject_records_review_feedback_for_owner(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(
        db_session,
        username="reject_owner",
        email="reject-owner@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="reject_admin",
        email="reject-admin@example.com",
        is_admin=True,
    )

    owner_token = await login(client, "reject_owner")
    admin_token = await login(client, "reject_admin")

    create_response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Needs Work Plugin",
            "slug": "needs-work-plugin",
            "description": "Needs more documentation",
        },
    )
    assert create_response.status_code == 201
    plugin = create_response.json()

    pending_status_list = await client.get("/api/v1/plugins?status=pending")
    assert pending_status_list.status_code == 403

    admin_pending_status_list = await client.get(
        "/api/v1/admin/plugins?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_pending_status_list.status_code == 200
    assert admin_pending_status_list.json()["total"] == 1

    reject_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"comment": "缺少 README 和安装说明"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
    assert reject_response.json()["review_summary"]["stage"] == "rejected"
    assert reject_response.json()["review_summary"]["manual_review_notes"] == "缺少 README 和安装说明"

    rejected_reviews_response = await client.get(f"/api/v1/plugins/{plugin['id']}/reviews")
    assert rejected_reviews_response.status_code == 404

    rejected_status_list = await client.get("/api/v1/plugins?status=rejected")
    assert rejected_status_list.status_code == 403

    admin_rejected_status_list = await client.get(
        "/api/v1/admin/plugins?status=rejected",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_rejected_status_list.status_code == 200
    assert admin_rejected_status_list.json()["total"] == 1

    my_plugins_response = await client.get(
        "/api/v1/plugins/mine",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert my_plugins_response.status_code == 200
    my_plugin = my_plugins_response.json()[0]
    assert my_plugin["status"] == "rejected"
    assert my_plugin["review_summary"]["manual_review_notes"] == "缺少 README 和安装说明"


async def test_submit_review_requires_plugin_owner_or_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(
        db_session,
        username="review_owner",
        email="review-owner@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="review_intruder",
        email="review-intruder@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="review_admin",
        email="review-admin@example.com",
        is_admin=True,
    )

    owner_token = await login(client, "review_owner")
    intruder_token = await login(client, "review_intruder")

    create_response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Review Protected Plugin",
            "slug": "review-protected-plugin",
            "description": "Only the owner can submit this for review",
            "repo_url": "https://github.com/neko/n.e.k.o_plugin_review_protected",
        },
    )
    assert create_response.status_code == 201
    plugin = create_response.json()

    intruder_submit = await client.post(
        f"/api/v1/plugins/{plugin['id']}/submit-review",
        headers={"Authorization": f"Bearer {intruder_token}"},
        params={"repo_url": "https://github.com/neko/n.e.k.o_plugin_evil_fork"},
    )
    assert intruder_submit.status_code == 403

    owner_submit = await client.post(
        f"/api/v1/plugins/{plugin['id']}/submit-review",
        headers={"Authorization": f"Bearer {owner_token}"},
        params={"repo_url": "https://github.com/neko/n.e.k.o_plugin_review_protected"},
    )
    assert owner_submit.status_code == 200
    assert owner_submit.json()["stage"] == "submitted"

    intruder_active_review = await client.get(
        f"/api/v1/plugins/{plugin['id']}/active-review",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert intruder_active_review.status_code == 403

    owner_active_review = await client.get(
        f"/api/v1/plugins/{plugin['id']}/active-review",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_active_review.status_code == 200
    assert owner_active_review.json()["stage"] == "submitted"


async def test_plugin_review_permission_allows_non_admin_reviewer(
    client: AsyncClient,
    db_session: AsyncSession,
):
    owner = await create_test_user(
        db_session,
        username="permission_owner",
        email="permission-owner@example.com",
        is_admin=False,
    )
    reviewer = await create_test_user(
        db_session,
        username="permission_reviewer",
        email="permission-reviewer@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="permission_member",
        email="permission-member@example.com",
        is_admin=False,
    )
    await grant_permission(db_session, reviewer, "plugin:review")

    owner_token = await login(client, owner.username)
    reviewer_token = await login(client, reviewer.username)
    member_token = await login(client, "permission_member")

    create_response = await client.post(
        "/api/v1/plugins",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Permission Reviewed Plugin",
            "slug": "permission-reviewed-plugin",
            "description": "Reviewed by plugin:review permission",
        },
    )
    assert create_response.status_code == 201
    plugin = create_response.json()

    member_list = await client.get(
        "/api/v1/admin/plugins",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 403

    reviewer_list = await client.get(
        "/api/v1/admin/plugins?status=pending",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_list.status_code == 200
    assert reviewer_list.json()["total"] == 1

    approve_response = await client.post(
        f"/api/v1/admin/plugins/{plugin['id']}/approve",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"comment": "审核员权限通过"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


async def test_debug_auth_allows_plugin_upload_without_token(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "DEBUG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "DEBUG_AUTH_USERNAME", "debug_member")
    monkeypatch.setattr(settings, "DEBUG_AUTH_EMAIL", "debug-member@example.com")
    monkeypatch.setattr(settings, "DEBUG_AUTH_IS_ADMIN", False)

    create_response = await client.post(
        "/api/v1/plugins",
        json={
            "name": "Debug Plugin",
            "slug": "debug-plugin",
            "description": "Created by debug auth",
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["author_name"] == "debug_member"

    my_plugins_response = await client.get("/api/v1/plugins/mine")
    assert my_plugins_response.status_code == 200
    assert my_plugins_response.json()[0]["slug"] == "debug-plugin"
