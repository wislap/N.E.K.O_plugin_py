import pytest
from httpx import AsyncClient


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
