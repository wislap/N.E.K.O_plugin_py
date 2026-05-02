import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, grant_permission


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "password123") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_zone_admin_endpoints_require_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "member", "zone-member@example.com")
    await create_test_user(db_session, "admin", "zone-admin@example.com", is_admin=True)

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")

    public_list = await client.get("/api/v1/zones")
    assert public_list.status_code == 200

    create_params = {
        "name": "测试区",
        "slug": "test-zone",
        "description": "测试分区",
    }

    anonymous_create = await client.post("/api/v1/admin/zones", params=create_params)
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {member_token}"},
        params=create_params,
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {admin_token}"},
        params=create_params,
    )
    assert admin_create.status_code == 201
    zone_id = admin_create.json()["id"]

    admin_delete = await client.delete(
        f"/api/v1/admin/zones/{zone_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200


async def test_permission_admin_mutations_require_admin(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "member", "permission-member@example.com")
    await create_test_user(db_session, "admin", "permission-admin@example.com", is_admin=True)

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")

    permission_payload = {
        "code": "plugin:test",
        "name": "测试权限",
        "category": "plugin",
        "description": "测试权限",
    }

    anonymous_create = await client.post("/api/v1/permissions/create", json=permission_payload)
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/permissions/create",
        headers={"Authorization": f"Bearer {member_token}"},
        json=permission_payload,
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/permissions/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=permission_payload,
    )
    assert admin_create.status_code == 200

    member_list = await client.get(
        "/api/v1/permissions/list",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 200

    group_payload = {
        "code": "reviewers",
        "name": "审核员",
        "description": "测试权限组",
        "permission_codes": ["plugin:test"],
    }

    member_group_create = await client.post(
        "/api/v1/permissions/groups/create",
        headers={"Authorization": f"Bearer {member_token}"},
        json=group_payload,
    )
    assert member_group_create.status_code == 403

    admin_group_create = await client.post(
        "/api/v1/permissions/groups/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=group_payload,
    )
    assert admin_group_create.status_code == 200

    groups_response = await client.get(
        "/api/v1/permissions/groups",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert groups_response.status_code == 200
    assert groups_response.json()[0]["permissions"][0]["code"] == "plugin:test"


async def test_permission_management_permission_allows_non_admin_operator(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(
        db_session,
        "permission_operator",
        "permission-operator@example.com",
    )
    member = await create_test_user(
        db_session,
        "permission_target",
        "permission-target@example.com",
    )
    await create_test_user(
        db_session,
        "permission_plain",
        "permission-plain@example.com",
    )
    await grant_permission(db_session, operator, "system:permission")

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "permission_plain")

    permission_payload = {
        "code": "plugin:operator_test",
        "name": "操作员测试权限",
        "category": "plugin",
    }

    plain_create = await client.post(
        "/api/v1/permissions/create",
        headers={"Authorization": f"Bearer {plain_token}"},
        json=permission_payload,
    )
    assert plain_create.status_code == 403

    operator_create = await client.post(
        "/api/v1/permissions/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json=permission_payload,
    )
    assert operator_create.status_code == 200

    group_response = await client.post(
        "/api/v1/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "operator_reviewers",
            "name": "操作员审核组",
            "permission_codes": ["plugin:operator_test"],
        },
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["id"]

    assign_response = await client.post(
        f"/api/v1/permissions/users/{member.id}/assign",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"group_ids": [group_id]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["user"] == member.username


async def test_settings_and_logs_require_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "member", "settings-member@example.com")
    await create_test_user(db_session, "admin", "settings-admin@example.com", is_admin=True)

    member_token = await login(client, "member")
    admin_token = await login(client, "admin")

    member_settings = await client.get(
        "/api/v1/admin/settings",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_settings.status_code == 403

    admin_init = await client.post(
        "/api/v1/admin/settings/init",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_init.status_code == 200

    admin_settings = await client.get(
        "/api/v1/admin/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_settings.status_code == 200
    assert isinstance(admin_settings.json()["settings"], list)

    member_update = await client.put(
        "/api/v1/admin/settings/smtp_host",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"value": "smtp.example.com"},
    )
    assert member_update.status_code == 403

    admin_update = await client.put(
        "/api/v1/admin/settings/smtp_host",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"value": "smtp.example.com"},
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["key"] == "smtp_host"

    member_logs = await client.get(
        "/api/v1/logs/stats",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_logs.status_code == 403

    admin_logs = await client.get(
        "/api/v1/logs/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_logs.status_code == 200


async def test_permission_group_grants_non_admin_access(
    client: AsyncClient,
    db_session: AsyncSession,
):
    member = await create_test_user(db_session, "operator", "operator@example.com")
    await create_test_user(db_session, "admin", "permission-grant-admin@example.com", is_admin=True)

    member_token = await login(client, "operator")
    admin_token = await login(client, "admin")

    for permission in [
        {
            "code": "system:settings",
            "name": "系统设置",
            "category": "system",
        },
        {
            "code": "system:logs",
            "name": "系统日志",
            "category": "system",
        },
    ]:
        response = await client.post(
            "/api/v1/permissions/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=permission,
        )
        assert response.status_code == 200

    group_response = await client.post(
        "/api/v1/permissions/groups/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": "operators",
            "name": "操作员",
            "permission_codes": ["system:settings", "system:logs"],
        },
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["id"]

    assign_response = await client.post(
        f"/api/v1/permissions/users/{member.id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"group_ids": [group_id]},
    )
    assert assign_response.status_code == 200

    settings_response = await client.get(
        "/api/v1/admin/settings",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert settings_response.status_code == 200

    logs_response = await client.get(
        "/api/v1/logs/stats",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert logs_response.status_code == 200
