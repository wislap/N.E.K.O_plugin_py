"""Mock E2E for standalone plugin repo -> package -> market publish.

This test intentionally avoids real GitHub I/O. It exercises the author-side
N.E.K.O CLI against a temporary standalone plugin repository, then publishes the
generated .neko-plugin through the market backend's mocked GitHub Release path.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import create_test_user, login

pytestmark = pytest.mark.asyncio


def _find_neko_repo() -> Path | None:
    env_path = os.environ.get("NEKO_REPO_PATH")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if (candidate / "plugin" / "neko_plugin_cli").is_dir():
            return candidate

    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "N.E.K.O"
        if (candidate / "plugin" / "neko_plugin_cli").is_dir():
            return candidate
        sibling_candidate = parent.parent / "N.E.K.O"
        if (sibling_candidate / "plugin" / "neko_plugin_cli").is_dir():
            return sibling_candidate
    return None


def _run_neko_cli(neko_repo: Path, args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["uv", "run", "python", "-m", "plugin.neko_plugin_cli", *args],
        cwd=neko_repo,
        env={**os.environ, **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    return completed


async def test_standalone_plugin_repo_package_can_publish_from_mocked_github_release(
    tmp_path: Path,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
) -> None:
    """Generated standalone plugin package is accepted by publish-from-release."""

    neko_repo = _find_neko_repo()
    if neko_repo is None:
        pytest.skip("N.E.K.O checkout not found; set NEKO_REPO_PATH to run this E2E")

    plugin_id = "e2e_release_demo"
    owner = "alice"
    repo_name = f"n.e.k.o_plugin_{plugin_id}"
    tag = "v0.1.0"
    target_dir = tmp_path / "target"

    _run_neko_cli(
        neko_repo,
        [
            "init-repo",
            plugin_id,
            "--plugins-root",
            str(tmp_path),
            "--no-git",
            "--neko-repo",
            "Project-N-E-K-O/N.E.K.O",
        ],
    )
    plugin_repo_dir = tmp_path / repo_name
    assert plugin_repo_dir.is_dir()

    _run_neko_cli(
        neko_repo,
        [
            "check",
            plugin_id,
            "--plugins-root",
            str(tmp_path),
            "--release",
            "--market-release",
            "--skip-tests",
            "--target-dir",
            str(target_dir),
        ],
        env={
            "GITHUB_REPOSITORY": f"{owner}/{repo_name}",
            "GITHUB_REF_NAME": tag,
        },
    )

    package_path = target_dir / f"{plugin_id}.neko-plugin"
    asset_bytes = package_path.read_bytes()
    assert asset_bytes.startswith(b"PK")

    author = await create_test_user(db_session, owner, "alice@example.com")
    plugin = await make_plugin(
        author=author,
        repo_url=f"https://github.com/{owner}/{repo_name}",
        slug=plugin_id,
        name="E2E Release Demo",
    )
    token = await login(client, owner)
    release_url, expected_sha = mock_github_release(
        asset_bytes=asset_bytes,
        tag=tag,
        owner=owner,
        repo=repo_name,
        asset_name=f"{plugin_id}.neko-plugin",
    )

    response = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url, "channel": "stable", "changelog": "mock e2e"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == "0.1.0"
    assert body["package_sha256"] == expected_sha
    assert body["payload_hash"]
    assert body["release_url"] == release_url
    assert body["package_url"].endswith(f"{plugin_id}.neko-plugin")

    latest = await client.get(f"/api/v1/plugins/{plugin.id}/versions/latest")
    assert latest.status_code == 200, latest.text
    assert latest.json()["package_sha256"] == expected_sha
