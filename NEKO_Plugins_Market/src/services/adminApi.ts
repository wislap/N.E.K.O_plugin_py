import {
  del,
  delWithBody,
  normalizePlugins,
  post,
  put,
  queryString,
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
import { adminModules } from "@/lib/adminModules";

export type {
  DashboardStats,
  LogStats,
  Plugin,
  Role,
  SMTPSettings,
  SystemSetting,
  User
} from "@/services/api";

export interface UserPermissions {
  user_id: number;
  username: string;
  is_admin: boolean;
  permissions: string[];
  groups: string[];
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  sort_order: number;
  plugin_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ZoneAdminItem {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ServerKeyPair {
  id: number;
  name: string;
  public_key: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  activated_at?: string | null;
  deactivated_at?: string | null;
}

export type CategoryPayload = Omit<Category, "id" | "plugin_count" | "created_at" | "updated_at">;
export type ZonePayload = Omit<ZoneAdminItem, "id" | "created_at" | "updated_at">;

export function canAccessAdminPermission(permissionState: UserPermissions | null, permission?: string) {
  if (!permissionState) {
    return false;
  }
  if (permissionState.is_admin || permissionState.permissions.includes("*")) {
    return true;
  }
  return !permission || permissionState.permissions.includes(permission);
}

export function hasAnyAdminAccess(permissionState: UserPermissions | null) {
  return adminModules.some((module) => canAccessAdminPermission(permissionState, module.permission));
}

export const adminApi = {
  getMyPermissions() {
    return request<UserPermissions>("/permissions/users/me");
  },

  getDashboardStats(): Promise<DashboardStats> {
    return request<DashboardStats>("/admin/dashboard/stats");
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

  getCategories() {
    return request<Category[]>("/categories?with_count=true");
  },

  createCategory(data: CategoryPayload) {
    return post<Category>("/categories", data);
  },

  updateCategory(categoryId: number, data: Partial<CategoryPayload>) {
    return put<Category>(`/categories/${categoryId}`, data);
  },

  deleteCategory(categoryId: number) {
    return del<{ message: string }>(`/categories/${categoryId}`);
  },

  getAdminZones() {
    return request<ZoneAdminItem[]>("/admin/zones");
  },

  createZone(data: ZonePayload) {
    const query = queryString(data);
    return post<ZoneAdminItem & { message: string }>(`/admin/zones${query}`);
  },

  updateZone(zoneId: number, data: Partial<Omit<ZonePayload, "slug">>) {
    const query = queryString(data);
    return put<ZoneAdminItem & { message: string }>(`/admin/zones/${zoneId}${query}`, {});
  },

  deleteZone(zoneId: number) {
    return del<{ message: string }>(`/admin/zones/${zoneId}`);
  },

  getSignatureKeys() {
    return request<ServerKeyPair[]>("/signatures/admin/keys");
  },

  getDefaultPublicKey() {
    return request<ServerKeyPair>("/signatures/public-keys/default");
  },

  createSignatureKey(name: string, setAsDefault: boolean) {
    const query = queryString({ name, set_as_default: setAsDefault });
    return post<ServerKeyPair & { message: string }>(`/signatures/admin/keys${query}`);
  },

  deactivateSignatureKey(keypairId: number) {
    return post<{ message: string }>(`/signatures/admin/keys/${keypairId}/deactivate`);
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
