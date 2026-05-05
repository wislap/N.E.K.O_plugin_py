import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plugin, PluginStatus
from tests.conftest import create_test_user, grant_permission


pytestmark = pytest.mark.asyncio


async def login(client: AsyncClient, username: str, password: str = "password123") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_submitted_review(
    client: AsyncClient,
    owner_token: str,
    *,
    slug: str = "workspace-demo",
) -> dict:
    repo_slug = slug.replace("-", "_")
    draft_response = await client.post(
        "/api/v1/review/submissions/drafts",
        headers=auth(owner_token),
        json={
            "repo_url": f"https://github.com/wislap/n.e.k.o_plugin_{repo_slug}",
            "plugin_name": "Workspace Demo",
            "plugin_slug": slug,
            "description": "A plugin submitted through the new review workspace.",
            "short_description": "Workspace review",
            "zone_slug": "tools",
            "tags": ["工具", "审核"],
            "submitted_ref": "main",
            "resolved_commit": "a" * 40,
            "commit_url": f"https://github.com/wislap/n.e.k.o_plugin_{repo_slug}/commit/{'a' * 40}",
            "license_name": "MIT",
            "metadata": {"plugin_toml_path": "plugin.toml"},
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["status"] == "draft"
    assert draft["current_snapshot"]["metadata"]["plugin_toml_path"] == "plugin.toml"

    submit_response = await client.post(
        f"/api/v1/review/submissions/{draft['id']}/submit",
        headers=auth(owner_token),
        json={"note": "ready"},
    )
    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "submitted"
    return submitted


async def test_review_workspace_contract_blocks_critical_then_approves(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "workspace_owner", "workspace-owner@example.com")
    reviewer = await create_test_user(db_session, "workspace_reviewer", "workspace-reviewer@example.com")
    await grant_permission(db_session, reviewer, "plugin:review")

    owner_token = await login(client, "workspace_owner")
    reviewer_token = await login(client, "workspace_reviewer")
    submitted = await create_submitted_review(client, owner_token)

    overview_response = await client.get(
        "/api/v1/admin/review/overview",
        headers=auth(reviewer_token),
    )
    assert overview_response.status_code == 200
    assert overview_response.json()["submitted"] == 1

    start_response = await client.post(
        f"/api/v1/admin/review/submissions/{submitted['id']}/start",
        headers=auth(reviewer_token),
        json={"note": "checking GitHub materials"},
    )
    assert start_response.status_code == 200
    in_review = start_response.json()
    assert in_review["status"] == "in_review"
    case_id = in_review["current_review_case_id"]

    comment_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/comments",
        headers=auth(reviewer_token),
        json={
            "severity": "critical",
            "target_area": "security",
            "target_ref": "plugin.toml",
            "body": "网络权限说明缺失，不能直接通过。",
        },
    )
    assert comment_response.status_code == 201
    comment = comment_response.json()
    assert comment["is_resolved"] is False

    filtered_response = await client.get(
        "/api/v1/admin/review/submissions",
        headers=auth(reviewer_token),
        params={"q": "workspace", "severity": "critical", "unresolved_only": True},
    )
    assert filtered_response.status_code == 200
    assert filtered_response.json()["total"] == 1

    blocked_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/approve",
        headers=auth(reviewer_token),
        json={"summary": "try approve"},
    )
    assert blocked_response.status_code == 400
    assert "critical" in blocked_response.json()["detail"]

    resolve_response = await client.post(
        f"/api/v1/admin/review/comments/{comment['id']}/resolve",
        headers=auth(reviewer_token),
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["is_resolved"] is True

    approve_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/approve",
        headers=auth(reviewer_token),
        json={"summary": "材料完整，允许上架。"},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "closed"
    assert approved["decision"] == "approved"
    assert approved["plugin_id"] is not None

    plugin = await db_session.scalar(select(Plugin).where(Plugin.id == approved["plugin_id"]))
    assert plugin is not None
    assert plugin.status == PluginStatus.APPROVED
    assert plugin.slug == "workspace-demo"

    detail_response = await client.get(
        f"/api/v1/admin/review/submissions/{submitted['id']}",
        headers=auth(reviewer_token),
    )
    assert detail_response.status_code == 200
    event_types = [event["event_type"] for event in detail_response.json()["events"]]
    assert event_types == [
        "draft_created",
        "submitted",
        "review_started",
        "commented",
        "comment_resolved",
        "approved",
    ]


async def test_review_workspace_major_requires_force_and_reopen_keeps_history(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "workspace_owner2", "workspace-owner2@example.com")
    reviewer = await create_test_user(db_session, "workspace_reviewer2", "workspace-reviewer2@example.com")
    await grant_permission(db_session, reviewer, "plugin:review")
    owner_token = await login(client, "workspace_owner2")
    reviewer_token = await login(client, "workspace_reviewer2")
    submitted = await create_submitted_review(client, owner_token, slug="workspace-major")

    start_response = await client.post(
        f"/api/v1/admin/review/submissions/{submitted['id']}/start",
        headers=auth(reviewer_token),
        json={},
    )
    assert start_response.status_code == 200
    case_id = start_response.json()["current_review_case_id"]

    major_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/comments",
        headers=auth(reviewer_token),
        json={
            "severity": "major",
            "target_area": "metadata",
            "target_ref": "README.md",
            "body": "说明偏短，但不阻塞本次测试上架。",
        },
    )
    assert major_response.status_code == 201

    blocked_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/approve",
        headers=auth(reviewer_token),
        json={"summary": "approve without force"},
    )
    assert blocked_response.status_code == 400
    assert "major" in blocked_response.json()["detail"]

    approve_response = await client.post(
        f"/api/v1/admin/review/cases/{case_id}/approve",
        headers=auth(reviewer_token),
        json={"summary": "accept remaining major", "force": True},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["decision"] == "approved"

    reopen_response = await client.post(
        f"/api/v1/admin/review/submissions/{submitted['id']}/reopen",
        headers=auth(reviewer_token),
        json={"note": "mistaken approve, reopen for audit"},
    )
    assert reopen_response.status_code == 200
    reopened = reopen_response.json()
    assert reopened["status"] == "in_review"
    assert reopened["decision"] is None
    assert reopened["current_review_case_id"] != case_id

    owner_detail = await client.get(
        f"/api/v1/review/submissions/{submitted['id']}",
        headers=auth(owner_token),
    )
    assert owner_detail.status_code == 200
    assert len(owner_detail.json()["review_cases"]) == 2


async def test_owner_revision_supersedes_open_review_case(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "revision_owner", "revision-owner@example.com")
    reviewer = await create_test_user(db_session, "revision_reviewer", "revision-reviewer@example.com")
    await grant_permission(db_session, reviewer, "plugin:review")

    owner_token = await login(client, "revision_owner")
    reviewer_token = await login(client, "revision_reviewer")
    submitted = await create_submitted_review(client, owner_token, slug="revision-demo")

    start_response = await client.post(
        f"/api/v1/admin/review/submissions/{submitted['id']}/start",
        headers=auth(reviewer_token),
        json={"note": "first pass"},
    )
    assert start_response.status_code == 200
    first_case_id = start_response.json()["current_review_case_id"]

    comment_response = await client.post(
        f"/api/v1/admin/review/cases/{first_case_id}/comments",
        headers=auth(reviewer_token),
        json={
            "severity": "major",
            "target_area": "docs",
            "body": "README 需要补充使用方式。",
        },
    )
    assert comment_response.status_code == 201

    revision_response = await client.post(
        f"/api/v1/review/submissions/{submitted['id']}/revision",
        headers=auth(owner_token),
        json={
            "description": "A plugin submitted through the new review workspace. README updated.",
            "submitted_ref": "fix-readme",
            "resolved_commit": "b" * 40,
            "note": "已补充 README 使用方式。",
        },
    )
    assert revision_response.status_code == 200
    revised = revision_response.json()
    assert revised["status"] == "submitted"
    assert revised["current_review_case_id"] is None
    assert revised["current_snapshot"]["revision_number"] == 2
    assert revised["current_snapshot"]["submitted_ref"] == "fix-readme"
    assert len(revised["snapshots"]) == 2

    first_case = next(case for case in revised["review_cases"] if case["id"] == first_case_id)
    assert first_case["status"] == "closed"
    assert first_case["decision"] == "superseded"

    restart_response = await client.post(
        f"/api/v1/admin/review/submissions/{submitted['id']}/start",
        headers=auth(reviewer_token),
        json={"note": "second pass"},
    )
    assert restart_response.status_code == 200
    assert restart_response.json()["status"] == "in_review"
    assert restart_response.json()["current_review_case_id"] != first_case_id


async def test_review_workspace_permissions(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await create_test_user(db_session, "workspace_owner3", "workspace-owner3@example.com")
    await create_test_user(db_session, "workspace_plain", "workspace-plain@example.com")
    owner_token = await login(client, "workspace_owner3")
    plain_token = await login(client, "workspace_plain")
    submitted = await create_submitted_review(client, owner_token, slug="workspace-perms")

    admin_list_response = await client.get(
        "/api/v1/admin/review/submissions",
        headers=auth(plain_token),
    )
    assert admin_list_response.status_code == 403

    other_detail_response = await client.get(
        f"/api/v1/review/submissions/{submitted['id']}",
        headers=auth(plain_token),
    )
    assert other_detail_response.status_code == 403
