import {
  Archive,
  BarChart3,
  ClipboardList,
  FileText,
  FolderTree,
  KeyRound,
  Layers3,
  LayoutDashboard,
  Mail,
  Puzzle,
  Settings,
  Shield,
  Users
} from "lucide-react";
import { adminModules, type AdminModule } from "@/lib/adminModules";

const menuIcons = {
  dashboard: LayoutDashboard,
  pluginReview: Puzzle,
  reviewOverview: BarChart3,
  reviewWorkspace: ClipboardList,
  reviewArchive: Archive,
  users: Users,
  permissions: Shield,
  smtp: Mail,
  settings: Settings,
  logs: FileText,
  categories: FolderTree,
  zones: Layers3,
  signatures: KeyRound
};

export type AdminMenuItem = Omit<AdminModule, "children"> & {
  icon: typeof LayoutDashboard;
  children?: AdminMenuItem[];
};

function withMenuIcons(modules: AdminModule[]): AdminMenuItem[] {
  return modules
    .filter((module) => module.visible !== false)
    .map((module) => ({
      ...module,
      icon: menuIcons[module.key as keyof typeof menuIcons] ?? LayoutDashboard,
      children: module.children ? withMenuIcons(module.children) : undefined
    }));
}

export function flattenAdminMenu(items: AdminMenuItem[]): AdminMenuItem[] {
  return items.flatMap((item) => [item, ...(item.children ? flattenAdminMenu(item.children) : [])]);
}

export const adminMenuItems = withMenuIcons(adminModules);
export const flatAdminMenuItems = flattenAdminMenu(adminMenuItems);

export function getAdminTitle(pathname: string) {
  if (pathname === "/admin/change-password") {
    return "修改初始密码";
  }
  if (pathname === "/admin/plugins") {
    return "工作区";
  }
  return flatAdminMenuItems.find((item) => item.path === pathname)?.label ?? "管理后台";
}
