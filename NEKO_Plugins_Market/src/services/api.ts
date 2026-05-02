import type { Plugin as MarketPlugin, Rating, Review as MarketReview, Zone } from "@/types";
import { logError } from "@/lib/error-reporting";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const REQUEST_ID_HEADER = "X-Request-ID";

export class ApiError extends Error {
  status: number;
  path: string;
  method: string;
  requestId: string;
  detail?: unknown;
  responseBody?: unknown;

  constructor(message: string, options: {
    status: number;
    path: string;
    method: string;
    requestId: string;
    detail?: unknown;
    responseBody?: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.path = options.path;
    this.method = options.method;
    this.requestId = options.requestId;
    this.detail = options.detail;
    this.responseBody = options.responseBody;
  }
}

export interface User {
  id: number;
  username: string;
  email: string;
  display_name?: string | null;
  avatar_url?: string | null;
  is_admin: boolean;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Plugin {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  short_description?: string | null;
  author_id: number;
  author_name: string;
  version: string;
  download_url?: string | null;
  icon_url?: string | null;
  repo_url?: string | null;
  readme?: string | null;
  zone_id?: number | null;
  zone_slug?: string | null;
  tags?: string[];
  download_count: number;
  likes: number;
  rating_average: number;
  rating_count: number;
  status: "pending" | "approved" | "rejected" | "disabled" | string;
  is_featured: number;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
  review_summary?: {
    stage?: string | null;
    manual_review_notes?: string | null;
    review_feedback?: string | null;
    manual_reviewed_at?: string | null;
    completed_at?: string | null;
    ai_score?: number | null;
    ai_recommendation?: string | null;
  } | null;
}

export interface Role {
  id: number;
  code?: string;
  name: string;
  description: string;
  permissions: string[];
  user_count: number;
  is_system?: boolean;
}

export interface DashboardStats {
  totalUsers: number;
  totalPlugins: number;
  pendingPlugins: number;
  approvedPlugins: number;
  rejectedPlugins: number;
  recentUsers: number;
  recentPlugins: number;
}

export interface MarketStats {
  totalPlugins: number;
  totalDownloads: number;
  activeDevelopers: number;
  newPluginsThisWeek: number;
}

export interface SMTPSettings {
  host: string;
  port: number;
  user: string;
  password?: string;
  tls: boolean;
  from_email: string;
  enabled: boolean;
}

export interface SystemSetting {
  key: string;
  value: string | number | boolean | null;
  description?: string | null;
  group?: string | null;
  is_encrypted?: boolean;
  updated_at?: string;
}

export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  content?: string | null;
  target_url?: string | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface LogStats {
  review_logs?: number;
  sandbox_logs?: number;
  permission_audit_logs?: number;
  total_logs?: number;
  [key: string]: number | string | undefined;
}

interface LoginRequest {
  username: string;
  password: string;
}

interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  display_name?: string;
}

interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  has_next?: boolean;
  has_prev?: boolean;
}

export type RequestBody = unknown;

interface PluginCreateRequest {
  name: string;
  slug: string;
  description?: string;
  short_description?: string;
  repo_url?: string;
  zone_id?: number;
  zone_slug?: string;
  tags?: string[];
}

interface ReviewCreateRequest {
  rating: number;
  title?: string;
  content?: string;
}

type PluginQuery = {
  q?: string;
  category?: string;
  author?: string;
  sort_by?: "created_at" | "download_count" | "rating_average" | "name";
  sort_order?: "asc" | "desc";
  featured_only?: boolean;
  page?: number;
  page_size?: number;
};

function getToken() {
  return localStorage.getItem("token");
}

function createRequestId() {
  return `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  const method = options.method ?? "GET";
  const requestId = headers.get(REQUEST_ID_HEADER) ?? createRequestId();
  headers.set(REQUEST_ID_HEADER, requestId);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers
    });
  } catch (error) {
    const networkError = new ApiError(
      error instanceof Error ? error.message : "网络请求失败，请检查后端服务是否已启动。",
      {
        status: 0,
        path,
        method,
        requestId,
        detail: error
      }
    );
    logError(networkError, {
      severity: "error",
      title: "网络请求失败",
      context: { method, path, apiBaseUrl: API_BASE_URL, requestId }
    });
    throw networkError;
  }

  const responseRequestId = response.headers.get(REQUEST_ID_HEADER) ?? requestId;

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    let responseBody: unknown;
    let detail: unknown;
    try {
      const data = await response.clone().json() as { detail?: unknown };
      responseBody = data;
      detail = data.detail;
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((item) => {
            if (typeof item === "object" && item && "msg" in item) {
              return String((item as { msg: unknown }).msg);
            }
            return String(item);
          })
          .join("；");
      }
    } catch {
      const text = await response.text();
      responseBody = text;
      message = text || message;
    }
    const error = new ApiError(message, {
      status: response.status,
      path,
      method,
      requestId: responseRequestId,
      detail,
      responseBody
    });
    logError(error, {
      severity: response.status >= 500 ? "error" : "warn",
      title: "API 请求失败",
      context: {
        method,
        path,
        status: response.status,
        requestId: responseRequestId,
        responseBody
      }
    });
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function post<T>(path: string, body?: RequestBody) {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export function put<T>(path: string, body: RequestBody) {
  return request<T>(path, {
    method: "PUT",
    body: JSON.stringify(body)
  });
}

export function del<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

export function delWithBody<T>(path: string, body: RequestBody) {
  return request<T>(path, {
    method: "DELETE",
    body: JSON.stringify(body)
  });
}

export function normalizePlugins(data: Plugin[] | PaginatedResponse<Plugin>): Plugin[] {
  return Array.isArray(data) ? data : data.items;
}

function fallbackRating(): Rating {
  return {
    functionality: "B",
    security: "B",
    documentation: "B",
    ratedAt: new Date(0).toISOString()
  };
}

function zoneSlugFromId(zoneId?: number | null): MarketPlugin["zone"] {
  const zones: MarketPlugin["zone"][] = ["game", "companion", "function", "entertainment", "tool"];
  if (!zoneId || zoneId < 1 || zoneId > zones.length) {
    return "function";
  }
  return zones[zoneId - 1];
}

function githubOwner(repoUrl?: string | null) {
  if (!repoUrl) {
    return "";
  }

  try {
    const url = new URL(repoUrl);
    return url.hostname === "github.com" ? url.pathname.split("/").filter(Boolean)[0] ?? "" : "";
  } catch {
    return "";
  }
}

function githubProfile(repoUrl?: string | null) {
  const owner = githubOwner(repoUrl);
  return owner ? `https://github.com/${owner}` : "";
}

function toMarketPlugin(plugin: Plugin): MarketPlugin {
  const description = plugin.description ?? plugin.short_description ?? "";
  const rating = fallbackRating();

  return {
    id: String(plugin.id),
    name: plugin.name,
    description,
    version: plugin.version,
    author: {
      name: plugin.author_name,
      avatar: plugin.icon_url ?? "",
      github: githubProfile(plugin.repo_url)
    },
    githubRepo: plugin.repo_url ?? "",
    downloadUrl: plugin.download_url ?? plugin.repo_url ?? "",
    zone: (plugin.zone_slug as MarketPlugin["zone"] | null) ?? zoneSlugFromId(plugin.zone_id),
    tags: plugin.tags ?? [],
    downloads: plugin.download_count,
    likes: plugin.likes ?? 0,
    aiRating: rating,
    adminRating: rating,
    readme: plugin.readme ?? description,
    createdAt: plugin.created_at,
    updatedAt: plugin.updated_at,
    isRecommended: Boolean(plugin.is_featured)
  };
}

function toMarketReview(review: {
  id: number;
  plugin_id: number;
  rating: number;
  title?: string | null;
  content?: string | null;
  created_at: string;
  author?: {
    username: string;
    display_name?: string | null;
    avatar_url?: string | null;
  } | null;
}): MarketReview {
  const userName = review.author?.display_name || review.author?.username || "匿名用户";

  return {
    id: String(review.id),
    pluginId: String(review.plugin_id),
    user: {
      name: userName,
      avatar: review.author?.avatar_url ?? ""
    },
    rating: review.rating,
    title: review.title ?? undefined,
    content: review.content ?? "",
    likes: 0,
    createdAt: review.created_at
  };
}

export function queryString(params: Record<string, unknown>) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function recentCount(items: Array<{ created_at: string }>) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => new Date(item.created_at).getTime() >= weekAgo).length;
}

function recentMarketCount(items: Array<{ createdAt: string }>) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => new Date(item.createdAt).getTime() >= weekAgo).length;
}

export function toRole(group: {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_system?: boolean;
  permissions?: Array<{ code: string }>;
}): Role {
  return {
    id: group.id,
    code: group.code,
    name: group.name,
    description: group.description ?? "",
    permissions: group.permissions?.map((permission) => permission.code) ?? [],
    user_count: 0,
    is_system: group.is_system ?? false
  };
}

export function roleCodeFromName(name: string) {
  const normalized = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `custom_${normalized || Date.now()}`;
}

export const authApi = {
  register(data: RegisterRequest) {
    return post<LoginResponse>("/auth/register", data);
  },

  debugLogin() {
    return post<LoginResponse>("/auth/debug-login");
  },

  login(credentials: LoginRequest) {
    return post<LoginResponse>("/auth/login", credentials);
  },

  getCurrentUser() {
    return request<User>("/auth/me");
  },

  changePassword(data: PasswordChangeRequest) {
    return post<User>("/auth/change-password", data);
  },

  logout() {
    return post<{ message: string }>("/auth/logout");
  }
};

export const pluginsApi = {
  async list(params: PluginQuery = {}) {
    const data = await request<PaginatedResponse<Plugin>>(`/plugins${queryString(params)}`);
    return {
      ...data,
      items: data.items.map(toMarketPlugin)
    };
  },

  async featured(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/featured?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async popular(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/popular?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async newest(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/newest?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async getById(id: string) {
    const data = await request<Plugin>(`/plugins/${id}`);
    return toMarketPlugin(data);
  },

  mine() {
    return request<Plugin[]>("/plugins/mine");
  },

  create(data: PluginCreateRequest) {
    return post<Plugin>("/plugins", data);
  },

  recordDownload(pluginId: string) {
    return post<{ message: string; success: boolean }>(`/plugins/${pluginId}/download`);
  }
};

export const reviewsApi = {
  async list(pluginId: string) {
    const data = await request<PaginatedResponse<{
      id: number;
      plugin_id: number;
      rating: number;
      title?: string | null;
      content?: string | null;
      created_at: string;
      author?: {
        username: string;
        display_name?: string | null;
        avatar_url?: string | null;
      } | null;
    }>>(`/plugins/${pluginId}/reviews`);

    return {
      ...data,
      items: data.items.map(toMarketReview)
    };
  },

  async create(pluginId: string, data: ReviewCreateRequest) {
    const review = await post<{
      id: number;
      plugin_id: number;
      rating: number;
      title?: string | null;
      content?: string | null;
      created_at: string;
      author?: {
        username: string;
        display_name?: string | null;
        avatar_url?: string | null;
      } | null;
    }>(`/plugins/${pluginId}/reviews`, data);

    return toMarketReview(review);
  }
};

export const zonesApi = {
  list() {
    return request<Zone[]>("/zones");
  }
};

export const marketApi = {
  async getStats(): Promise<MarketStats> {
    const data = await pluginsApi.list({ page_size: 100 });
    const plugins = data.items;

    return {
      totalPlugins: data.total,
      totalDownloads: plugins.reduce((total, plugin) => total + plugin.downloads, 0),
      activeDevelopers: new Set(plugins.map((plugin) => plugin.author.name)).size,
      newPluginsThisWeek: recentMarketCount(plugins)
    };
  }
};

export const notificationsApi = {
  list(limit = 20) {
    return request<Notification[]>(`/notifications?limit=${limit}`);
  },

  unreadCount() {
    return request<{ count: number }>("/notifications/unread-count");
  },

  markRead(notificationId: number) {
    return post<Notification>(`/notifications/${notificationId}/read`);
  },

  markAllRead() {
    return post<{ message: string; success: boolean }>("/notifications/read-all");
  }
};
