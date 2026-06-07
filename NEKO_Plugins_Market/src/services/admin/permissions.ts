import {
  del,
  post,
  put,
  request
} from "@/services/http/client";
import type { Permission, Role } from "@/services/types";
import { roleCodeFromName, toRole } from "@/services/utils";

type PermissionGroupResponse = {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_system?: boolean;
  is_active?: boolean;
  level?: number;
  user_count?: number;
  group_type?: string | null;
  permissions?: Array<{ code: string }>;
};

export function getPermissions(category?: string) {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return request<Permission[]>(`/admin/permissions/list${query}`);
}

export async function getRoles() {
  const groups = await request<PermissionGroupResponse[]>("/admin/permissions/groups");
  return groups.map(toRole);
}

export async function createRole(data: Omit<Role, "id" | "user_count">) {
  const group = await post<PermissionGroupResponse>("/admin/permissions/groups/create", {
    code: data.code || roleCodeFromName(data.name),
    name: data.name,
    description: data.description,
    level: data.level,
    permission_codes: data.permissions
  });
  return toRole(group);
}

export async function updateRole(roleId: number, data: Partial<Role>) {
  const group = await put<PermissionGroupResponse>(`/admin/permissions/groups/${roleId}`, {
    name: data.name,
    description: data.description,
    level: data.level,
    is_active: data.is_active,
    permission_codes: data.permissions
  });
  return toRole(group);
}

export async function deleteRole(roleId: number) {
  return del<{ message: string }>(`/admin/permissions/groups/${roleId}`);
}

export function assignRolesToUser(userId: number, roleIds: number[]) {
  return post<{ message: string; user: string; groups: string[]; roles: string[] }>(
    `/admin/permissions/users/${userId}/assign`,
    { group_ids: roleIds }
  );
}
