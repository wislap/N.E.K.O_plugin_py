import {
  del,
  delWithBody,
  post,
  put,
  request,
  roleCodeFromName,
  toRole,
  type Role
} from "@/services/api";

type PermissionGroupResponse = {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  is_system?: boolean;
  permissions?: Array<{ code: string }>;
};

export async function getRoles() {
  const groups = await request<PermissionGroupResponse[]>("/admin/permissions/groups");
  return groups.map(toRole);
}

export async function createRole(data: Omit<Role, "id" | "user_count">) {
  const group = await post<PermissionGroupResponse>("/admin/permissions/groups/create", {
    code: data.code || roleCodeFromName(data.name),
    name: data.name,
    description: data.description,
    permission_codes: data.permissions
  });
  return toRole(group);
}

export async function updateRole(roleId: number, data: Partial<Role>) {
  const currentRoles = await getRoles();
  const currentRole = currentRoles.find((role) => role.id === roleId);
  const group = await put<PermissionGroupResponse>(`/admin/permissions/groups/${roleId}`, {
    name: data.name,
    description: data.description
  });

  if (data.permissions && currentRole) {
    const currentPermissions = new Set(currentRole.permissions);
    const nextPermissions = new Set(data.permissions);
    const toAdd = data.permissions.filter((code) => !currentPermissions.has(code));
    const toRemove = currentRole.permissions.filter((code) => !nextPermissions.has(code));

    if (toAdd.length > 0) {
      await post(`/admin/permissions/groups/${roleId}/permissions`, toAdd);
    }
    if (toRemove.length > 0) {
      await delWithBody(`/admin/permissions/groups/${roleId}/permissions`, toRemove);
    }
  }

  const roles = await getRoles();
  return roles.find((role) => role.id === roleId) ?? toRole(group);
}

export async function deleteRole(roleId: number) {
  return del<{ message: string }>(`/admin/permissions/groups/${roleId}`);
}
