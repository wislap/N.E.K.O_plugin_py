import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import (
    Permission,
    PermissionAuditLog,
    PermissionGroup,
    permission_group_items,
    user_permission_groups,
)
from app.models.plugin import Plugin, PluginStatus
from app.services.permission_service import PermissionService
from tests.conftest import create_test_user, grant_permission


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "Str0ngPass!42") -> str:
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

    anonymous_create = await client.post("/api/v1/admin/zones", json=create_params)
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {member_token}"},
        json=create_params,
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=create_params,
    )
    assert admin_create.status_code == 201
    zone_id = admin_create.json()["id"]

    admin_delete = await client.delete(
        f"/api/v1/admin/zones/{zone_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete.status_code == 200


async def test_legacy_admin_paths_are_not_kept(client: AsyncClient):
    checks = [
        await client.get("/api/v1/users"),
        await client.post("/api/v1/categories", json={"name": "旧分类", "slug": "legacy-category"}),
        await client.post("/api/v1/signatures/admin/keys", json={"name": "legacy-key"}),
        await client.get("/api/v1/logs/stats"),
        await client.get("/api/v1/permissions/list"),
        await client.post("/api/v1/plugins/1/approve", json={"comment": "legacy"}),
    ]

    for response in checks:
        assert response.status_code in {404, 405}


async def test_zone_management_permission_allows_non_admin_operator(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(db_session, "zone_operator", "zone-operator@example.com")
    await create_test_user(db_session, "zone_plain", "zone-plain@example.com")
    await grant_permission(db_session, operator, "plugin:zone")

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "zone_plain")

    plain_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {plain_token}"},
        json={
            "name": "普通用户分区",
            "slug": "plain-zone",
        },
    )
    assert plain_create.status_code == 403

    plain_list = await client.get(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert plain_list.status_code == 403

    operator_create = await client.post(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "权限分区",
            "slug": "operator-zone",
            "description": "由分区管理员创建",
        },
    )
    assert operator_create.status_code == 201
    assert operator_create.json()["slug"] == "operator-zone"

    operator_list = await client.get(
        "/api/v1/admin/zones",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert operator_list.status_code == 200
    assert operator_list.json()[0]["id"] == operator_create.json()["id"]


async def test_category_management_permission_allows_non_admin_operator(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(db_session, "category_operator", "category-operator@example.com")
    await create_test_user(db_session, "category_plain", "category-plain@example.com")
    await grant_permission(db_session, operator, "plugin:category")

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "category_plain")

    plain_create = await client.post(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {plain_token}"},
        json={
            "name": "普通分类",
            "slug": "plain-category",
        },
    )
    assert plain_create.status_code == 403

    operator_create = await client.post(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "权限分类",
            "slug": "operator-category",
            "description": "由分类管理员创建",
        },
    )
    assert operator_create.status_code == 201
    assert operator_create.json()["slug"] == "operator-category"


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

    anonymous_create = await client.post("/api/v1/admin/permissions/create", json=permission_payload)
    assert anonymous_create.status_code in {401, 403}

    member_create = await client.post(
        "/api/v1/admin/permissions/create",
        headers={"Authorization": f"Bearer {member_token}"},
        json=permission_payload,
    )
    assert member_create.status_code == 403

    admin_create = await client.post(
        "/api/v1/admin/permissions/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=permission_payload,
    )
    assert admin_create.status_code == 200

    member_list = await client.get(
        "/api/v1/admin/permissions/list",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_list.status_code == 403

    group_payload = {
        "code": "reviewers",
        "name": "审核员",
        "description": "测试权限组",
        "permission_codes": ["plugin:test"],
    }

    member_group_create = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {member_token}"},
        json=group_payload,
    )
    assert member_group_create.status_code == 403

    admin_group_create = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=group_payload,
    )
    assert admin_group_create.status_code == 200

    groups_response = await client.get(
        "/api/v1/admin/permissions/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert groups_response.status_code == 200
    assert groups_response.json()[0]["permissions"][0]["code"] == "plugin:test"


async def test_role_management_permission_allows_non_admin_operator_but_not_permission_definition(
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
    await grant_permission(db_session, operator, "system:role")
    await PermissionService().ensure_permission_system(db_session, "plugin:review")
    await db_session.commit()

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "permission_plain")

    permission_payload = {
        "code": "plugin:operator_test",
        "name": "操作员测试权限",
        "category": "plugin",
    }

    plain_create = await client.post(
        "/api/v1/admin/permissions/create",
        headers={"Authorization": f"Bearer {plain_token}"},
        json=permission_payload,
    )
    assert plain_create.status_code == 403

    operator_create = await client.post(
        "/api/v1/admin/permissions/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json=permission_payload,
    )
    assert operator_create.status_code == 403

    group_response = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "operator_reviewers",
            "name": "操作员审核组",
            "permission_codes": ["plugin:review"],
        },
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["id"]

    assign_response = await client.post(
        f"/api/v1/admin/permissions/users/{member.id}/assign",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"group_ids": [group_id]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["user"] == member.username


async def test_legacy_system_permission_no_longer_grants_role_management(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(
        db_session,
        "legacy_permission_operator",
        "legacy-permission-operator@example.com",
    )
    legacy_permission = Permission(
        code="system:permission",
        name="旧权限管理",
        category="system",
        is_active=True,
    )
    legacy_role = PermissionGroup(
        code="legacy_permission_managers",
        name="旧权限管理员",
        level=100,
        is_active=True,
        is_system=False,
    )
    db_session.add_all([legacy_permission, legacy_role])
    await db_session.flush()
    await db_session.execute(
        permission_group_items.insert().values(
            group_id=legacy_role.id,
            permission_id=legacy_permission.id,
        )
    )
    await db_session.execute(
        user_permission_groups.insert().values(
            user_id=operator.id,
            group_id=legacy_role.id,
        )
    )
    await db_session.commit()

    operator_token = await login(client, operator.username)

    groups_response = await client.get(
        "/api/v1/admin/permissions/groups",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert groups_response.status_code == 403

    me_response = await client.get(
        "/api/v1/admin/permissions/users/me",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert me_response.status_code == 200
    assert "system:permission" not in me_response.json()["permissions"]


async def test_permission_audit_log_uses_outer_transaction(
    db_session: AsyncSession,
):
    admin = await create_test_user(
        db_session,
        "audit_admin",
        "audit-admin@example.com",
        is_admin=True,
    )
    service = PermissionService()

    await service._log_action(
        db_session,
        "create",
        "group",
        1,
        "rollback probe",
        operator_id=admin.id,
    )
    await db_session.rollback()

    result = await db_session.execute(select(PermissionAuditLog))
    assert result.scalars().all() == []


async def test_permission_management_level_bounds_role_operations(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(
        db_session,
        "role_level_operator",
        "role-level-operator@example.com",
    )
    member = await create_test_user(
        db_session,
        "role_level_target",
        "role-level-target@example.com",
    )
    admin = await create_test_user(
        db_session,
        "role_level_admin",
        "role-level-admin@example.com",
        is_admin=True,
    )
    await grant_permission(db_session, operator, "system:role", level=100)

    operator_token = await login(client, operator.username)
    admin_token = await login(client, admin.username)

    low_role = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "low_level_reviewers",
            "name": "低等级审核员",
            "level": 99,
            "permission_codes": ["system:role"],
        },
    )
    assert low_role.status_code == 200
    assert low_role.json()["level"] == 99

    reserved_role = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "super_admin",
            "name": "伪超管角色",
            "level": 99,
            "permission_codes": ["system:role"],
        },
    )
    assert reserved_role.status_code == 400
    assert "系统保留" in reserved_role.json()["detail"]

    equal_role = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "equal_level_reviewers",
            "name": "同级审核员",
            "level": 100,
            "permission_codes": ["system:role"],
        },
    )
    assert equal_role.status_code == 403

    super_level_role = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "code": "fake_super_admin",
            "name": "伪超管",
            "level": 1000,
            "permission_codes": ["system:role"],
        },
    )
    assert super_level_role.status_code == 400

    high_role = await client.post(
        "/api/v1/admin/permissions/groups/create",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": "high_level_reviewers",
            "name": "高等级审核员",
            "level": 150,
            "permission_codes": ["system:role"],
        },
    )
    assert high_role.status_code == 200

    assign_high_role = await client.post(
        f"/api/v1/admin/permissions/users/{member.id}/assign",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"group_ids": [high_role.json()["id"]]},
    )
    assert assign_high_role.status_code == 403


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
        "/api/v1/admin/logs/stats",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_logs.status_code == 403

    admin_logs = await client.get(
        "/api/v1/admin/logs/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_logs.status_code == 200


async def test_signature_management_permission_allows_non_admin_operator(
    client: AsyncClient,
    db_session: AsyncSession,
):
    operator = await create_test_user(db_session, "signature_operator", "signature-operator@example.com")
    await create_test_user(db_session, "signature_plain", "signature-plain@example.com")
    await grant_permission(db_session, operator, "plugin:signature")

    operator_token = await login(client, operator.username)
    plain_token = await login(client, "signature_plain")

    plain_keys = await client.get(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert plain_keys.status_code == 403

    operator_create = await client.post(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"name": "测试签名密钥", "set_as_default": True},
    )
    assert operator_create.status_code == 201
    assert operator_create.json()["name"] == "测试签名密钥"

    operator_keys = await client.get(
        "/api/v1/admin/signatures/keys",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert operator_keys.status_code == 200
    assert operator_keys.json()[0]["name"] == "测试签名密钥"


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
            "/api/v1/admin/permissions/create",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=permission,
        )
        assert response.status_code == 200

    group_response = await client.post(
        "/api/v1/admin/permissions/groups/create",
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
        f"/api/v1/admin/permissions/users/{member.id}/assign",
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
        "/api/v1/admin/logs/stats",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert logs_response.status_code == 200


async def test_dashboard_stats_are_scoped_by_permission(
    client: AsyncClient,
    db_session: AsyncSession,
):
    owner = await create_test_user(db_session, "dash_owner", "dash-owner@example.com")
    reviewer = await create_test_user(db_session, "dash_reviewer", "dash-reviewer@example.com")
    user_operator = await create_test_user(db_session, "dash_user_operator", "dash-users@example.com")
    await create_test_user(db_session, "dash_plain", "dash-plain@example.com")
    await create_test_user(db_session, "dash_admin", "dash-admin@example.com", is_admin=True)
    await grant_permission(db_session, reviewer, "plugin:review")
    await grant_permission(db_session, user_operator, "system:user")

    db_session.add_all([
        Plugin(
            name="Approved Dashboard Plugin",
            slug="approved-dashboard-plugin",
            author_id=owner.id,
            author_name=owner.username,
            status=PluginStatus.APPROVED,
        ),
    ])
    await db_session.commit()

    plain_token = await login(client, "dash_plain")
    reviewer_token = await login(client, reviewer.username)
    user_operator_token = await login(client, user_operator.username)
    admin_token = await login(client, "dash_admin")

    plain_response = await client.get(
        "/api/v1/admin/dashboard/stats",
        headers={"Authorization": f"Bearer {plain_token}"},
    )
    assert plain_response.status_code == 403

    reviewer_response = await client.get(
        "/api/v1/admin/dashboard/stats",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert reviewer_response.status_code == 200
    reviewer_stats = reviewer_response.json()
    assert reviewer_stats["totalUsers"] == 0
    assert reviewer_stats["totalPlugins"] == 1
    assert reviewer_stats["pendingPlugins"] == 0
    assert reviewer_stats["approvedPlugins"] == 1
    assert reviewer_stats["rejectedPlugins"] == 0

    user_operator_response = await client.get(
        "/api/v1/admin/dashboard/stats",
        headers={"Authorization": f"Bearer {user_operator_token}"},
    )
    assert user_operator_response.status_code == 200
    user_stats = user_operator_response.json()
    assert user_stats["totalUsers"] == 5
    assert user_stats["totalPlugins"] == 0

    admin_response = await client.get(
        "/api/v1/admin/dashboard/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == 200
    admin_stats = admin_response.json()
    assert admin_stats["totalUsers"] == 5
    assert admin_stats["totalPlugins"] == 1
