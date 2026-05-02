import {
  del,
  delWithBody,
  normalizePlugins,
  post,
  put,
  queryString,
  recentCount,
  request,
  roleCodeFromName,
  toRole,
  type DashboardStats,
  type LogStats,
  type PaginatedResponse,
  type Plugin,
  type Role,
  type SMTPSettings,
  type SystemSetting,
  type User
} from "@/services/api";

export type {
  DashboardStats,
  LogStats,
  Plugin,
  Role,
  SMTPSettings,
  SystemSetting,
  User
} from "@/services/api";

export const adminApi = {
  async getDashboardStats(): Promise<DashboardStats> {
    const [usersPage, plugins] = await Promise.all([
      this.getUsers({ page: 1, page_size: 100 }).catch(() => ({ items: [] as User[], total: 0 })),
      this.getAllPlugins().catch(() => [] as Plugin[])
    ]);
    const users = usersPage.items;

    return {
      totalUsers: usersPage.total,
      totalPlugins: plugins.length,
      pendingPlugins: plugins.filter((plugin) => plugin.status === "pending").length,
      approvedPlugins: plugins.filter((plugin) => plugin.status === "approved").length,
      rejectedPlugins: plugins.filter((plugin) => plugin.status === "rejected").length,
      recentUsers: recentCount(users),
      recentPlugins: recentCount(plugins)
    };
  },

  getUsers(params: { q?: string; page?: number; page_size?: number } = {}) {
    const query = queryString(params);
    return request<PaginatedResponse<User>>(`/users${query}`);
  },

  async getAllUsers() {
    const data = await this.getUsers({ page: 1, page_size: 100 });
    return data.items;
  },

  updateUser(userId: number, data: Partial<User>) {
    return put<User>(`/users/${userId}`, data);
  },

  deleteUser(userId: number) {
    return del<{ message: string }>(`/users/${userId}`);
  },

  async getAllPlugins() {
    const data = await request<Plugin[] | PaginatedResponse<Plugin>>("/admin/plugins?page_size=100");
    return normalizePlugins(data);
  },

  approvePlugin(pluginId: number, comment?: string) {
    return post<Plugin>(`/plugins/${pluginId}/approve`, { comment: comment?.trim() || null });
  },

  rejectPlugin(pluginId: number, comment?: string) {
    return post<Plugin>(`/plugins/${pluginId}/reject`, { comment: comment?.trim() || null });
  },

  async getRoles() {
    const groups = await request<Array<{
      id: number;
      code: string;
      name: string;
      description?: string | null;
      is_system?: boolean;
      permissions?: Array<{ code: string }>;
    }>>("/permissions/groups");
    return groups.map(toRole);
  },

  async createRole(data: Omit<Role, "id" | "user_count">) {
    const group = await post<{
      id: number;
      code: string;
      name: string;
      description?: string | null;
      is_system?: boolean;
      permissions?: Array<{ code: string }>;
    }>("/permissions/groups/create", {
      code: data.code || roleCodeFromName(data.name),
      name: data.name,
      description: data.description,
      permission_codes: data.permissions
    });
    return toRole(group);
  },

  async updateRole(roleId: number, data: Partial<Role>) {
    const currentRoles = await this.getRoles();
    const currentRole = currentRoles.find((role) => role.id === roleId);
    const group = await put<{
      id: number;
      code: string;
      name: string;
      description?: string | null;
      is_system?: boolean;
      permissions?: Array<{ code: string }>;
    }>(`/permissions/groups/${roleId}`, {
      name: data.name,
      description: data.description
    });

    if (data.permissions && currentRole) {
      const currentPermissions = new Set(currentRole.permissions);
      const nextPermissions = new Set(data.permissions);
      const toAdd = data.permissions.filter((code) => !currentPermissions.has(code));
      const toRemove = currentRole.permissions.filter((code) => !nextPermissions.has(code));

      if (toAdd.length > 0) {
        await post(`/permissions/groups/${roleId}/permissions`, toAdd);
      }
      if (toRemove.length > 0) {
        await delWithBody(`/permissions/groups/${roleId}/permissions`, toRemove);
      }
    }

    const roles = await this.getRoles();
    return roles.find((role) => role.id === roleId) ?? toRole(group);
  },

  async deleteRole(roleId: number) {
    return del<{ message: string }>(`/permissions/groups/${roleId}`);
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
