from __future__ import annotations

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, login

pytestmark = pytest.mark.asyncio


async def test_release_candidates_lists_github_releases_with_package_asset(
    client: AsyncClient,
    db_session: AsyncSession,
    make_plugin,
) -> None:
    author = await create_test_user(db_session, "alice", "alice@example.com")
    plugin = await make_plugin(
        author=author,
        repo_url="https://github.com/alice/n.e.k.o_plugin_demo",
    )
    token = await login(client, "alice")

    with respx.mock(assert_all_called=True) as router:
        router.get(
            "https://api.github.com/repos/alice/n.e.k.o_plugin_demo/releases",
            params={"per_page": "10"},
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "tag_name": "v0.1.0",
                        "name": "v0.1.0",
                        "html_url": "https://github.com/alice/n.e.k.o_plugin_demo/releases/tag/v0.1.0",
                        "published_at": "2026-05-19T05:12:13Z",
                        "draft": False,
                        "prerelease": False,
                        "assets": [
                            {"name": "demo.market-release-check.txt"},
                            {"name": "demo.neko-plugin"},
                        ],
                    }
                ],
            )
        )

        response = await client.get(
            f"/api/v1/plugins/{plugin.id}/versions/release-candidates",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == [
        {
            "tag_name": "v0.1.0",
            "name": "v0.1.0",
            "release_url": "https://github.com/alice/n.e.k.o_plugin_demo/releases/tag/v0.1.0",
            "published_at": "2026-05-19T05:12:13Z",
            "draft": False,
            "prerelease": False,
            "asset_names": ["demo.market-release-check.txt", "demo.neko-plugin"],
            "has_package_asset": True,
        }
    ]
