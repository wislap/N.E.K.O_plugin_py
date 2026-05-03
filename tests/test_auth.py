import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models import EmailVerificationToken, User
from app.services.bootstrap_service import BootstrapService
from app.services.email_verification_service import email_verification_service


pytestmark = pytest.mark.asyncio


async def test_health_check(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_register_login_and_get_current_user(client: AsyncClient, monkeypatch):
    async def fake_send(*args, **kwargs):
        return True

    monkeypatch.setattr(email_verification_service, "send_verification_email", fake_send)

    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123",
            "display_name": "Alice",
        },
    )

    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["user"]["username"] == "alice"
    assert register_data["user"]["is_email_verified"] is False
    assert register_data["verification_email_sent"] is True
    assert "access_token" in register_data
    assert "hashed_password" not in register_data["user"]

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"


async def test_register_creates_hashed_email_verification_token(
    client: AsyncClient,
    db_session,
    monkeypatch,
):
    captured = {}

    async def fake_send(db, user, raw_token):
        captured["raw_token"] = raw_token
        return True

    monkeypatch.setattr(email_verification_service, "send_verification_email", fake_send)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "verify_user",
            "email": "verify@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    assert "raw_token" in captured

    result = await db_session.execute(select(EmailVerificationToken))
    token = result.scalar_one()
    assert token.email == "verify@example.com"
    assert token.token_hash == email_verification_service.hash_token(captured["raw_token"])
    assert token.token_hash != captured["raw_token"]
    assert token.used_at is None
    assert token.is_active is True


async def test_verify_email_marks_user_verified_and_consumes_token(
    client: AsyncClient,
    db_session,
    monkeypatch,
):
    captured = {}

    async def fake_send(db, user, raw_token):
        captured["raw_token"] = raw_token
        return True

    monkeypatch.setattr(email_verification_service, "send_verification_email", fake_send)

    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "verify_target",
            "email": "verify-target@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201

    verify_response = await client.post(
        "/api/v1/auth/verify-email",
        params={"token": captured["raw_token"]},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["is_email_verified"] is True
    assert verify_response.json()["email_verified_at"] is not None

    user = await db_session.scalar(select(User).where(User.username == "verify_target"))
    assert user is not None
    assert user.email_verified_at is not None

    token = await db_session.scalar(select(EmailVerificationToken))
    assert token is not None
    assert token.used_at is not None
    assert token.is_active is False

    second_response = await client.post(
        "/api/v1/auth/verify-email",
        params={"token": captured["raw_token"]},
    )
    assert second_response.status_code == 400


async def test_resend_verification_email_uses_authenticated_user(
    client: AsyncClient,
    monkeypatch,
):
    async def fake_send(*args, **kwargs):
        return True

    monkeypatch.setattr(email_verification_service, "send_verification_email", fake_send)

    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "resend_user",
            "email": "resend@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]

    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", 0)
    resend_response = await client.post(
        "/api/v1/auth/resend-verification-email",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resend_response.status_code == 200
    assert resend_response.json()["already_verified"] is False
    assert resend_response.json()["verification_email_sent"] is True


async def test_bootstrap_initial_admin_must_change_password(
    client: AsyncClient,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "root")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "root@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "password")

    await BootstrapService.ensure_initial_admin(db_session)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "password"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["is_admin"] is True
    assert login_response.json()["user"]["must_change_password"] is True

    token = login_response.json()["access_token"]
    change_response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "password", "new_password": "new-password"},
    )

    assert change_response.status_code == 200
    assert change_response.json()["must_change_password"] is False
