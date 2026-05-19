import { post, request } from "./http/client";
import type {
  PluginVersion,
  VersionReleaseCandidate,
  VersionPublishRequest,
  VersionYankRequest,
  VersionYankResponse
} from "./types";

interface ListParams {
  channel?: "stable" | "beta";
  /** 默认 false；版本管理 UI 一般传 true 以便显示已撤回历史 */
  includeYanked?: boolean;
}

/** 错误码 → 中文文案；与后端 `app/errors/version_errors.py` 对齐。 */
export const VERSION_ERROR_MESSAGES: Record<string, string> = {
  forbidden: "没有权限",
  release_repo_mismatch: "GitHub release 不属于此插件的仓库",
  release_asset_not_found: "未在此 release 中找到 .neko-plugin / .neko-bundle 资产",
  release_asset_too_large: "release 资产超过 200 MiB 上限",
  release_publish_failed: "拉取或处理 release 失败，请稍后重试",
  version_already_exists: "该版本号已存在",
  version_already_yanked: "该版本已被撤回",
  latest_version_not_found: "该插件在此 channel 暂无可用版本",
  invalid_channel: "不支持的 channel"
};

/** 从 axios / fetch 错误对象里提取 backend 的 code → 中文文案。 */
export function getVersionErrorMessage(
  err: unknown,
  fallback = "操作失败"
): string {
  // 后端响应 JSON 形如 {"detail": "...", "code": "..."}
  // 客户端 ApiError 把它存放在 responseBody 中（services/http/errors.ts）
  const body = (err as { responseBody?: { detail?: string; code?: string } })?.responseBody;
  if (body?.code && VERSION_ERROR_MESSAGES[body.code]) {
    return VERSION_ERROR_MESSAGES[body.code];
  }
  if (body?.detail) return body.detail;
  // axios 风格 fallback（以防未来切到 axios）
  const axiosLike = (err as { response?: { data?: { detail?: string; code?: string } } })?.response
    ?.data;
  if (axiosLike?.code && VERSION_ERROR_MESSAGES[axiosLike.code]) {
    return VERSION_ERROR_MESSAGES[axiosLike.code];
  }
  if (axiosLike?.detail) return axiosLike.detail;
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export const versionsApi = {
  list(pluginId: number, params: ListParams = {}) {
    const search = new URLSearchParams();
    if (params.channel) search.set("channel", params.channel);
    if (params.includeYanked !== undefined)
      search.set("include_yanked", String(params.includeYanked));
    const qs = search.toString();
    return request<PluginVersion[]>(`/plugins/${pluginId}/versions${qs ? `?${qs}` : ""}`);
  },

  latest(pluginId: number, channel: "stable" | "beta" = "stable") {
    return request<PluginVersion>(`/plugins/${pluginId}/versions/latest?channel=${channel}`);
  },

  releaseCandidates(pluginId: number) {
    return request<VersionReleaseCandidate[]>(`/plugins/${pluginId}/versions/release-candidates`);
  },

  publishFromRelease(pluginId: number, body: VersionPublishRequest) {
    return post<PluginVersion>(
      `/plugins/${pluginId}/versions/publish-from-release`,
      body
    );
  },

  yank(pluginId: number, versionId: number, body: VersionYankRequest) {
    return post<VersionYankResponse>(
      `/plugins/${pluginId}/versions/${versionId}/yank`,
      body
    );
  }
};
