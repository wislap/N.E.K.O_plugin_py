import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.bootstrap_service import BootstrapService


pytestmark = pytest.mark.asyncio


async def test_health_check(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_register_login_and_get_current_user(client: AsyncClient):
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
