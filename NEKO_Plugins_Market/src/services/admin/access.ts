import { adminModules } from "@/lib/adminModules";
import type { AdminModule } from "@/lib/adminModules";
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
  if (!permission) {
    return true;
  }
  return permissionState.permissions.includes(permission);
}

function flattenModules(modules: AdminModule[]): AdminModule[] {
  return modules.flatMap((module) => [module, ...(module.children ? flattenModules(module.children) : [])]);
}

export function hasAnyAdminAccess(permissionState: UserPermissions | null) {
  if (!permissionState) {
    return false;
  }
  if (permissionState.is_admin || permissionState.permissions.includes("*")) {
    return true;
  }
  return flattenModules(adminModules).some((module) => (
    typeof module.permission === "string"
      && canAccessAdminPermission(permissionState, module.permission)
  ));
}
