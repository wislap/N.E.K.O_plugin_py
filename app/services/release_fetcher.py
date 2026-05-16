"""GitHub Release 拉取与资产解析。

负责把作者提交的 release_url 转为冻结到 Version 表的 `ResolvedRelease`
事实集，期间字节级算 sha256，强校验 owner/repo 与 plugin.repo_url 一致。

关键约束：
- 资产下载强制 `Accept-Encoding: identity`，避免 httpx 自动 gzip 解压
  造成 sha256 与服务端字节流不一致（违反 P0）。
- ZIP 体内 `metadata.toml` 解析失败一律 fallback 到 `payload_hash=None`，
  绝不让 publish 整体挂掉（R3.9 / P4 鲁棒性）。
- 网络瞬时故障重试一次，仍失败抛 `release_publish_failed`。

设计文档：
`Plugin Market (Backend + Frontend)/.kiro/specs/market-version-management/design.md`
§"Release_Fetcher" 节。
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import re
import tomllib
import zipfile
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.errors.version_errors import ReleaseFetchError

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_MAX_ASSET_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_DOWNLOAD_CHUNK = 64 * 1024
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
RETRY_BACKOFF_SECONDS = 0.5
ALLOWED_ASSET_SUFFIXES = (".neko-plugin", ".neko-bundle")

_RELEASE_URL_TAG_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/releases/tag/(?P<tag>[^/?#]+)/?$",
    re.IGNORECASE,
)
_RELEASE_URL_ID_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/releases/(?P<rid>\d+)/?$",
    re.IGNORECASE,
)
_SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA64_RE = re.compile(r"^[0-9a-fA-F]{64}$")



@dataclass(frozen=True)
class ResolvedRelease:
    """`ReleaseFetcher.fetch_and_resolve` 的成功返回值。

    所有字段都是后端从 GitHub 抓取并校验后的事实，写入 Version 表后视为
    `Frozen_Fact`，不允许通过任何 PATCH 接口修改。
    """

    package_url: str  # asset 的 browser_download_url
    package_sha256: str  # 64 字符 lowercase hex
    payload_hash: str | None  # metadata.toml [payload].hash，缺失/非法为 None
    release_tag: str  # 已去除前导 v/V，例如 "1.2.0"
    release_url_canonical: str  # release HTML 页 URL
    source_commit: str  # 40 字符 lowercase hex commit sha
    asset_filename: str
    asset_bytes_size: int


def _parse_repo_path(url: str) -> tuple[str, str]:
    """从 GitHub 仓库 URL 抠出 (owner, repo)，统一小写返回。"""
    parsed = urlparse(url)
    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ReleaseFetchError(
            "release_repo_mismatch", f"非 GitHub 仓库 URL: {url}"
        )
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ReleaseFetchError(
            "release_repo_mismatch", f"无法解析 owner/repo: {url}"
        )
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner.lower(), repo.lower()


def _parse_release_url(url: str) -> tuple[str, str, str | None, str | None]:
    """从 release_url 抠出 (owner, repo, tag, release_id)。

    `tag` 与 `release_id` 至少有一个非 None。
    """
    if m := _RELEASE_URL_TAG_RE.match(url):
        return m["owner"].lower(), m["repo"].lower(), m["tag"], None
    if m := _RELEASE_URL_ID_RE.match(url):
        return m["owner"].lower(), m["repo"].lower(), None, m["rid"]
    raise ReleaseFetchError(
        "release_repo_mismatch",
        f"release_url 必须是 https://github.com/<o>/<r>/releases/tag/<tag> 或 /releases/<id>: {url}",
    )



class ReleaseFetcher:
    """协调 GitHub release 拉取、资产下载、sha256 计算、metadata.toml 解析。

    构造参数:
        http_client_factory: 注入自定义 httpx.AsyncClient 工厂（测试用）。
            默认 `lambda: httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True)`。
        max_asset_bytes: 资产体积上限。
        github_token: 优先使用此 token，否则从 settings.GITHUB_TOKEN 取。
    """

    def __init__(
        self,
        *,
        http_client_factory=None,
        max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
        github_token: str | None = None,
    ) -> None:
        self._client_factory = http_client_factory or self._default_client_factory
        self._max_asset_bytes = max_asset_bytes
        self._token = github_token or getattr(settings, "GITHUB_TOKEN", None)

    @staticmethod
    def _default_client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    def _api_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "N.E.KO-Plugin-Market",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers

    def _asset_headers(self) -> dict[str, str]:
        # 关键: identity 防止 httpx 解 gzip 让 sha256 与服务端字节流偏移
        headers = {
            "Accept": "application/octet-stream",
            "User-Agent": "N.E.KO-Plugin-Market",
            "Accept-Encoding": "identity",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers


    async def fetch_and_resolve(
        self,
        *,
        release_url: str,
        plugin_repo_url: str,
    ) -> ResolvedRelease:
        """主入口：拉 release → 校验 owner/repo → 下载 asset → 算 sha256 →
        解析 metadata.toml → 解析 commit sha → 返回 `ResolvedRelease`。
        """
        rel_owner, rel_repo, tag, release_id = _parse_release_url(release_url)
        plugin_owner, plugin_repo = _parse_repo_path(plugin_repo_url)

        if rel_owner != plugin_owner or rel_repo != plugin_repo:
            raise ReleaseFetchError(
                "release_repo_mismatch",
                "GitHub release 不属于此插件的仓库",
            )

        async with self._client_factory() as client:
            release_data = await self._fetch_release_metadata(
                client, owner=rel_owner, repo=rel_repo, tag=tag, release_id=release_id
            )
            asset = self._pick_asset(release_data)
            asset_bytes, package_sha256 = await self._stream_download_asset(
                client, asset_url=asset["browser_download_url"]
            )
            payload_hash = _parse_metadata_toml(asset_bytes)
            source_commit = await self._resolve_commit_sha(
                client,
                owner=rel_owner,
                repo=rel_repo,
                target_commitish=release_data.get("target_commitish") or "",
            )

        release_tag_clean = re.sub(r"^[vV]", "", str(release_data.get("tag_name") or ""))
        if not release_tag_clean:
            raise ReleaseFetchError(
                "release_publish_failed", "release 缺少 tag_name 字段"
            )

        return ResolvedRelease(
            package_url=asset["browser_download_url"],
            package_sha256=package_sha256,
            payload_hash=payload_hash,
            release_tag=release_tag_clean,
            release_url_canonical=str(
                release_data.get("html_url") or release_url
            ),
            source_commit=source_commit,
            asset_filename=str(asset.get("name") or ""),
            asset_bytes_size=len(asset_bytes),
        )


    async def _fetch_release_metadata(
        self,
        client: httpx.AsyncClient,
        *,
        owner: str,
        repo: str,
        tag: str | None,
        release_id: str | None,
    ) -> dict:
        """GET /releases/tags/{tag} 或 /releases/{id}。404 视为致命错误。"""
        if tag is not None:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/tags/{tag}"
        else:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases/{release_id}"

        resp = await self._request_with_retry(client, "GET", url, headers=self._api_headers())
        if resp.status_code == 404:
            raise ReleaseFetchError(
                "release_publish_failed", "GitHub release 不存在"
            )
        if resp.status_code >= 400:
            raise ReleaseFetchError(
                "release_publish_failed",
                f"GitHub release 接口返回 {resp.status_code}",
            )
        return resp.json()

    @staticmethod
    def _pick_asset(release_data: dict) -> dict:
        """选 release.assets 中第一个 .neko-plugin / .neko-bundle 资产。"""
        assets = release_data.get("assets") or []
        for asset in assets:
            name = str(asset.get("name") or "").lower()
            if any(name.endswith(suffix) for suffix in ALLOWED_ASSET_SUFFIXES):
                if asset.get("browser_download_url"):
                    return asset
        raise ReleaseFetchError(
            "release_asset_not_found",
            "未在此 release 中找到 .neko-plugin / .neko-bundle 资产",
        )


    async def _stream_download_asset(
        self,
        client: httpx.AsyncClient,
        *,
        asset_url: str,
    ) -> tuple[bytes, str]:
        """流式下载并增量计算 sha256；超过上限抛 release_asset_too_large。"""
        # 一些上游对未授权请求的资产 URL 会返回 302 → S3 签名 URL，
        # follow_redirects=True 已配置，handler 透明跟进。
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                async with client.stream(
                    "GET", asset_url, headers=self._asset_headers()
                ) as resp:
                    if resp.status_code >= 500 or resp.status_code in (408, 429):
                        raise httpx.HTTPStatusError(
                            f"asset stream HTTP {resp.status_code}",
                            request=resp.request,
                            response=resp,
                        )
                    if resp.status_code >= 400:
                        raise ReleaseFetchError(
                            "release_publish_failed",
                            f"下载资产失败 HTTP {resp.status_code}",
                        )

                    hasher = hashlib.sha256()
                    buffer = io.BytesIO()
                    total = 0
                    async for chunk in resp.aiter_bytes(chunk_size=DEFAULT_DOWNLOAD_CHUNK):
                        total += len(chunk)
                        if total > self._max_asset_bytes:
                            raise ReleaseFetchError(
                                "release_asset_too_large",
                                f"release 资产超过 {self._max_asset_bytes // (1024 * 1024)} MiB 上限",
                            )
                        hasher.update(chunk)
                        buffer.write(chunk)
                    return buffer.getvalue(), hasher.hexdigest()
            except ReleaseFetchError:
                raise
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            ) as exc:
                last_exc = exc
                if attempt == 0:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                break
            except httpx.HTTPError as exc:
                last_exc = exc
                break
        raise ReleaseFetchError(
            "release_publish_failed",
            f"下载资产失败: {last_exc!s}",
        )


    async def _resolve_commit_sha(
        self,
        client: httpx.AsyncClient,
        *,
        owner: str,
        repo: str,
        target_commitish: str,
    ) -> str:
        """target_commitish 是 40-hex 直接返回；否则 GET /commits/{ref} 拿 sha。"""
        if not target_commitish:
            return ""
        if _SHA40_RE.match(target_commitish):
            return target_commitish.lower()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{target_commitish}"
        resp = await self._request_with_retry(client, "GET", url, headers=self._api_headers())
        if resp.status_code == 404:
            # 目标分支不存在不应该阻止发版 —— commit 信息只是 nice-to-have
            return ""
        if resp.status_code >= 400:
            return ""
        sha = str(resp.json().get("sha") or "")
        return sha.lower() if _SHA40_RE.match(sha) else ""

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> httpx.Response:
        """对幂等的 GitHub API GET 请求重试一次（5xx / 429 / 网络错误）。"""
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                resp = await client.request(method, url, headers=headers)
                if resp.status_code in (429,) or resp.status_code >= 500:
                    if attempt == 0:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                        continue
                return resp
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                last_exc = exc
                if attempt == 0:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                break
        raise ReleaseFetchError(
            "release_publish_failed",
            f"GitHub API 不可达: {last_exc!s}" if last_exc else "GitHub API 不可达",
        )



def _parse_metadata_toml(asset_bytes: bytes) -> str | None:
    """从 .neko-plugin/.neko-bundle (ZIP) 中读 metadata.toml 的 [payload].hash。

    任何异常（坏 ZIP、缺文件、坏 TOML、非 64-hex）都吞掉返回 None，
    确保发版流程对资产元数据缺失保持鲁棒（R3.9 / P4）。
    """
    try:
        with zipfile.ZipFile(io.BytesIO(asset_bytes)) as zf:
            try:
                info = zf.getinfo("metadata.toml")
            except KeyError:
                return None
            with zf.open(info) as fp:
                raw = fp.read()
        text = raw.decode("utf-8")
        data = tomllib.loads(text)
    except (
        zipfile.BadZipFile,
        KeyError,
        tomllib.TOMLDecodeError,
        UnicodeDecodeError,
        OSError,
    ):
        return None

    payload_section = data.get("payload")
    if not isinstance(payload_section, dict):
        return None
    raw_hash = payload_section.get("hash")
    if not isinstance(raw_hash, str):
        return None
    if not _SHA64_RE.fullmatch(raw_hash):
        return None
    return raw_hash.lower()


__all__ = [
    "ALLOWED_ASSET_SUFFIXES",
    "DEFAULT_MAX_ASSET_BYTES",
    "ReleaseFetcher",
    "ResolvedRelease",
]
