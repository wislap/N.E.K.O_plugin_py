import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerificationToken
from app.models.plugin import Plugin, PluginStatus
from app.core.time import utc_now
from tests.conftest import create_test_user, grant_permission


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "Str0ngPass!42") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_user_list_requires_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(
        db_session,
        username="member",
        email="member@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="admin",
        email="admin-permissions@example.com",
        is_admin=True,
    )

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")

    anonymous_response = await client.get("/api/v1/admin/users")
    assert anonymous_response.status_code in {401, 403}

    member_response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_response.status_code == 403

    admin_response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == 200
    assert admin_response.json()["total"] == 2
    assert len(admin_response.json()["items"]) == 2

    search_response = await client.get(
        "/api/v1/admin/users?q=member&page=1&page_size=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1
    assert search_response.json()["items"][0]["username"] == "member"


async def test_user_admin_safety_guards(
    client: AsyncClient,
    db_session: AsyncSession,
):
    admin = await create_test_user(
        db_session,
        username="safe_admin",
        email="safe-admin@example.com",
        is_admin=True,
    )
    member = await create_test_user(
        db_session,
        username="safe_member",
        email="safe-member@example.com",
        is_admin=False,
    )

    admin_token = await login(client, "safe_admin")

    self_delete = await client.delete(
        f"/api/v1/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert self_delete.status_code == 400

    demote_last_admin = await client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_admin": False},
    )
    assert demote_last_admin.status_code == 400

    disable_last_admin = await client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert disable_last_admin.status_code == 400

    promote_member = await client.put(
        f"/api/v1/admin/users/{member.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_admin": True, "username": "safe_reviewer"},
    )
    assert promote_member.status_code == 200
    assert promote_member.json()["is_admin"] is True
    assert promote_member.json()["username"] == "safe_reviewer"

    demote_original_admin = await client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_admin": False},
    )
    assert demote_original_admin.status_code == 200


async def test_user_management_permission_allows_non_admin_operator(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(
        db_session,
        username="user_operator",
        email="user-operator@example.com",
        is_admin=False,
    )
    target = await create_test_user(
        db_session,
        username="managed_member",
        email="managed-member@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="plain_member",
        email="plain-member@example.com",
        is_admin=False,
    )
    await grant_permission(db_session, operator, "system:user")

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "plain_member")

    plain_list = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert plain_list.status_code == 403

    operator_list = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert operator_list.status_code == 200
    assert operator_list.json()["total"] == 3

    update_response = await client.put(
        f"/api/v1/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"is_active": False, "username": "managed_member_disabled"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
    assert update_response.json()["username"] == "managed_member_disabled"


async def test_delete_user_cleans_auth_records_but_blocks_business_data(
    client: AsyncClient,
    db_session: AsyncSession,
):
    admin = await create_test_user(
        db_session,
        username="delete_admin",
        email="delete-admin@example.com",
        is_admin=True,
    )
    stale_user = await create_test_user(
        db_session,
        username="stale_user",
        email="stale-user@example.com",
        email_verified=False,
    )
    token = EmailVerificationToken(
        user_id=stale_user.id,
        email=stale_user.email,
        token_hash="a" * 64,
        expires_at=utc_now(),
        is_active=True,
    )
    db_session.add(token)

    author = await create_test_user(
        db_session,
        username="plugin_author_user",
        email="plugin-author-user@example.com",
    )
    plugin = Plugin(
        name="owned plugin",
        slug="owned-plugin",
        author_id=author.id,
        author_name=author.username,
        status=PluginStatus.APPROVED,
        tags=[],
    )
    db_session.add(plugin)
    await db_session.commit()

    admin_token = await login(client, admin.username)

    stale_delete = await client.delete(
        f"/api/v1/admin/users/{stale_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stale_delete.status_code == 200

    author_delete = await client.delete(
        f"/api/v1/admin/users/{author.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert author_delete.status_code == 409
    assert "业务数据" in author_delete.json()["detail"]


async def test_category_mutations_require_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(
        db_session,
        username="member",
        email="category-member@example.com",
        is_admin=False,
    )
    await create_test_user(
        db_session,
        username="admin",
        email="category-admin@example.com",
        is_admin=True,
    )

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")
    payload = {
        "name": "工具",
        "slug": "tools",
        "description": "工具类插件",
    }

    anonymous_response = await client.post("/api/v1/admin/categories", json=payload)
    assert anonymous_response.status_code in {401, 403}

    member_response = await client.post(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {member_token}"},
        json=payload,
    )
    assert member_response.status_code == 403

    admin_response = await client.post(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert admin_response.status_code == 201
    category_id = admin_response.json()["id"]

    delete_member_response = await client.delete(
        f"/api/v1/admin/categories/{category_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert delete_member_response.status_code == 403

    delete_admin_response = await client.delete(
        f"/api/v1/admin/categories/{category_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_admin_response.status_code == 200
