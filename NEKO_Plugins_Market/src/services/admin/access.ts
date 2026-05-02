import { adminModules } from "@/lib/adminModules";
import { request } from "@/services/http/client";
import type { UserPermissions } from "./types";

export function getMyPermissions() {
  return request<UserPermissions>("/admin/permissions/users/me");
}

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
