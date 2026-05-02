import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_request_id_header_is_generated(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req-")


async def test_request_id_header_is_preserved(client: AsyncClient):
    response = await client.get(
        "/health",
        headers={"X-Request-ID": "web-test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "web-test-request-123"


async def test_invalid_request_id_header_is_replaced(client: AsyncClient):
    response = await client.get(
        "/health",
        headers={"X-Request-ID": "bad request id"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req-")


async def test_request_id_header_is_added_to_error_responses(client: AsyncClient):
    response = await client.get(
        "/missing",
        headers={"X-Request-ID": "web-not-found-123"},
    )

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "web-not-found-123"


async def test_cors_exposes_request_id_header(client: AsyncClient):
    response = await client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
