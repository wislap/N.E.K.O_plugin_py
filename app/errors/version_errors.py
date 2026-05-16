"""版本管理子系统的错误类型与到 HTTP 状态码的映射。

所有抛出的 `VersionDomainError` 都会被 `app.main` 注册的全局 exception
handler 捕获并转成 ``{"detail": ..., "code": ...}`` 的统一 JSON 响应。

设计要点：
- 单一错误基类 `VersionDomainError(code, message)`，code 是稳定字符串，
  前端按 code 查文案表，后端调用方按 code 决定行为。
- `ReleaseFetchError` 是 `VersionDomainError` 的 alias，仅作语义分类
  （来自 GitHub release 拉取流程），共用同一个 handler。
- `ERROR_CODE_TO_HTTP` 是 code → HTTP 状态码的全集，handler 命中
  时使用；缺失 fallback 为 500。
"""

from __future__ import annotations

# 错误码到 HTTP 状态码的映射。新增错误码时同步更新本字典与文档错误码表。
ERROR_CODE_TO_HTTP: dict[str, int] = {
    "forbidden": 403,
    "release_repo_mismatch": 400,
    "release_asset_not_found": 400,
    "release_asset_too_large": 413,
    "release_publish_failed": 502,
    "version_already_exists": 409,
    "version_already_yanked": 409,
    "latest_version_not_found": 404,
    "invalid_channel": 400,
}


class VersionDomainError(Exception):
    """版本管理领域错误基类。

    Attributes:
        code: 稳定的错误码字符串，与 `ERROR_CODE_TO_HTTP` 的 key 对应。
        message: 给最终用户看的可读消息（中文）。
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ReleaseFetchError(VersionDomainError):
    """`Release_Fetcher` 抛出的错误（GitHub release 拉取 / 下载 / 解析）。

    继承 `VersionDomainError` 以共用全局 handler；保留独立类便于在测试
    与服务层做 isinstance 区分。
    """

    pass


__all__ = [
    "ERROR_CODE_TO_HTTP",
    "ReleaseFetchError",
    "VersionDomainError",
]
