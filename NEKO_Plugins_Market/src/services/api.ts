import type { Plugin as MarketPlugin, Rating, Zone } from "@/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
}

export interface Role {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  user_count: number;
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

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  has_next?: boolean;
  has_prev?: boolean;
}

type RequestBody = unknown;

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const data = await response.json() as { detail?: string };
      message = data.detail ?? message;
    } catch {
      const text = await response.text();
      message = text || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function post<T>(path: string, body?: RequestBody) {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

function put<T>(path: string, body: RequestBody) {
  return request<T>(path, {
    method: "PUT",
    body: JSON.stringify(body)
  });
}

function del<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

function normalizePlugins(data: Plugin[] | PaginatedResponse<Plugin>): Plugin[] {
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

function queryString(params: PluginQuery) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

function recentCount(items: Array<{ created_at: string }>) {
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return items.filter((item) => new Date(item.created_at).getTime() >= weekAgo).length;
}

let rolesStore: Role[] = [
  {
    id: 1,
    name: "超级管理员",
    description: "拥有所有权限",
    permissions: ["plugin_review", "plugin_manage", "user_manage", "system_setting", "log_view", "smtp_setting"],
    user_count: 1
  },
  {
    id: 2,
    name: "审核员",
    description: "负责插件审核",
    permissions: ["plugin_review", "log_view"],
    user_count: 0
  }
];

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
  }
};

export const zonesApi = {
  list() {
    return request<Zone[]>("/zones");
  }
};

export const adminApi = {
  async getDashboardStats(): Promise<DashboardStats> {
    const [users, plugins] = await Promise.all([
      this.getAllUsers().catch(() => [] as User[]),
      this.getAllPlugins().catch(() => [] as Plugin[])
    ]);

    return {
      totalUsers: users.length,
      totalPlugins: plugins.length,
      pendingPlugins: plugins.filter((plugin) => plugin.status === "pending").length,
      approvedPlugins: plugins.filter((plugin) => plugin.status === "approved").length,
      rejectedPlugins: plugins.filter((plugin) => plugin.status === "rejected").length,
      recentUsers: recentCount(users),
      recentPlugins: recentCount(plugins)
    };
  },

  getAllUsers() {
    return request<User[]>("/users");
  },

  updateUser(userId: number, data: Partial<User>) {
    return put<User>(`/users/${userId}`, data);
  },

  deleteUser(userId: number) {
    return del<{ message: string }>(`/users/${userId}`);
  },

  async getAllPlugins() {
    const approved = await request<Plugin[] | PaginatedResponse<Plugin>>("/plugins?status=approved&page_size=100");
    const pending = await request<Plugin[] | PaginatedResponse<Plugin>>("/plugins?status=pending&page_size=100").catch(
      () => ({ items: [] as Plugin[], total: 0 })
    );
    const rejected = await request<Plugin[] | PaginatedResponse<Plugin>>("/plugins?status=rejected&page_size=100").catch(
      () => ({ items: [] as Plugin[], total: 0 })
    );

    return [
      ...normalizePlugins(approved),
      ...normalizePlugins(pending),
      ...normalizePlugins(rejected)
    ];
  },

  approvePlugin(pluginId: number) {
    return post<Plugin>(`/plugins/${pluginId}/approve`);
  },

  rejectPlugin(pluginId: number, comment?: string) {
    void comment;
    return post<Plugin>(`/plugins/${pluginId}/reject`);
  },

  async getRoles() {
    return rolesStore;
  },

  async createRole(data: Omit<Role, "id" | "user_count">) {
    const role = {
      ...data,
      id: Date.now(),
      user_count: 0
    };
    rolesStore = [...rolesStore, role];
    return role;
  },

  async updateRole(roleId: number, data: Partial<Role>) {
    rolesStore = rolesStore.map((role) =>
      role.id === roleId ? { ...role, ...data } : role
    );
    const role = rolesStore.find((item) => item.id === roleId);
    if (!role) {
      throw new Error("角色不存在");
    }
    return role;
  },

  async deleteRole(roleId: number) {
    rolesStore = rolesStore.filter((role) => role.id !== roleId);
    return { message: "角色已删除" };
  },

  getSMTPSettings() {
    return request<SMTPSettings>("/admin/settings/smtp");
  },

  updateSMTPSettings(data: SMTPSettings) {
    return put<{ message: string }>("/admin/settings/smtp", data);
  },

  testSMTP(toEmail: string) {
    return post<{ success: boolean; message: string }>("/admin/settings/smtp/test", {
      to_email: toEmail
    });
  },

  getSettings() {
    return request<{ settings: SystemSetting[] }>("/admin/settings");
  },

  initSettings() {
    return post<{ message: string }>("/admin/settings/init");
  },

  updateSetting(key: string, value: string | number | boolean | null) {
    return put<{ message: string; key: string; value?: string | number | boolean | null }>(
      `/admin/settings/${encodeURIComponent(key)}`,
      { value }
    );
  },

  getLogStats() {
    return request<LogStats>("/logs/stats");
  },

  cleanupLogs(logType = "all") {
    return post<{ message: string; deleted_count: number }>(`/logs/cleanup?log_type=${encodeURIComponent(logType)}`);
  },

  getRetentionSettings() {
    return request<Record<string, number>>("/logs/retention-settings");
  }
};
