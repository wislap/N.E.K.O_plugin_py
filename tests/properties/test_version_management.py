"""Property-based tests for market-version-management.

实现 P0：发版后下载链路 sha256 严格一致（spec 灵魂条款）。

其他 properties 的覆盖说明：
- **P1**（is_latest 唯一性）由数据库 partial unique index
  `uq_versions_plugin_channel_latest` 强约束（见 `app/models/version.py`），
  并由 `tests/integration/test_publish_from_release.py::test_publish_from_release_switches_is_latest`
  与 `tests/integration/test_yank.py::test_yank_latest_promotes_next_version`
  example-based 覆盖。
- **P2**（yank 后晋级一致性）由
  `tests/integration/test_yank.py::test_yank_latest_promotes_next_version`
  与 `test_yank_only_version_clears_latest` 覆盖。
- **P3**（并发同 release_url 幂等）由
  `tests/integration/test_publish_from_release.py::test_publish_from_release_version_already_exists`
  覆盖；真正的多 worker 并发场景由 partial unique index 强约束兜底，
  本仓库使用单 worker + SQLite，PBT 测试架构（共享 db_session + asyncio.gather）
  无法可靠复现真并发，故未在此处实现。
- **P4**（metadata.toml 解析鲁棒性）由 `_parse_metadata_toml` 内 try/except
  兜底覆盖；未来如需 PBT 化可在此追加。
"""

from __future__ import annotations

import hashlib
import re

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    build_zip_with_metadata,
    create_test_user,
    login,
)

pytestmark = pytest.mark.asyncio


_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


# 每个 hypothesis example 共享 function-scoped fixture（client/db_session/...），
# 因此用单调递增计数器为每例分配唯一 username / slug / tag，避免
# UNIQUE 约束撞车导致的 FlakyReplay。
_p0_counter = {"i": 0}


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(payload=st.binary(min_size=0, max_size=4096))
async def test_p0_package_sha256_matches_asset_bytes(
    payload: bytes,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_github_release,
    make_plugin,
):
    """**Property P0: 发版后下载链路 sha256 严格一致**

    对任意 payload 字节流：
    1. 后端写入的 `package_sha256` == sha256(asset_bytes).hexdigest().lower()
    2. `package_sha256` 是 64 字符 lowercase hex
    3. asset 字节流前 4 字节是 ZIP magic（隐式：build_zip_with_metadata 出 ZIP）

    Validates: spec R0.1 / R0.2 / R0.3 / R0.4 / R3.8
    """
    _p0_counter["i"] += 1
    idx = _p0_counter["i"]
    username = f"alice_{idx}"
    repo = f"plugin{idx}"

    author = await create_test_user(
        db_session, username, f"{username}@example.com"
    )
    plugin = await make_plugin(
        author=author,
        repo_url=f"https://github.com/{username}/{repo}",
        slug=f"slug-p0-{idx}",
        name=f"plugin-p0-{idx}",
    )
    token = await login(client, username)

    asset_bytes = build_zip_with_metadata(payload)
    release_url, expected_sha = mock_github_release(
        asset_bytes=asset_bytes,
        tag="v1.0.0",
        owner=username,
        repo=repo,
    )

    resp = await client.post(
        f"/api/v1/plugins/{plugin.id}/versions/publish-from-release",
        headers={"Authorization": f"Bearer {token}"},
        json={"release_url": release_url, "channel": "stable"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # 性质 1: 字节级一致
    actual_sha = hashlib.sha256(asset_bytes).hexdigest()
    assert body["package_sha256"] == actual_sha
    assert body["package_sha256"] == expected_sha
    # 性质 2: 64 字符 lowercase hex
    assert _HEX_64.fullmatch(body["package_sha256"])
    # 性质 3: ZIP magic（asset_bytes 永远是合法 ZIP，前 4 字节固定）
    assert asset_bytes[:4] == b"PK\x03\x04"
