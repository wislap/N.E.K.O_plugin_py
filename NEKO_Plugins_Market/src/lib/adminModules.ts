export interface AdminModule {
  key: string;
  label: string;
  path: string;
  permission?: string;
  visible?: boolean;
  children?: AdminModule[];
}

export const adminModules: AdminModule[] = [
  { key: "dashboard", label: "仪表盘", path: "/admin" },
  {
    key: "pluginReview",
    label: "插件审核",
    path: "/admin/review/workspace",
    permission: "plugin:review",
    children: [
      { key: "reviewOverview", label: "总览", path: "/admin/review/overview", permission: "plugin:review" },
      { key: "reviewWorkspace", label: "工作区", path: "/admin/review/workspace", permission: "plugin:review" },
      { key: "reviewArchive", label: "归档", path: "/admin/review/archive", permission: "plugin:review" }
    ]
  },
  { key: "plugins", label: "插件管理", path: "/admin/plugins", permission: "plugin:manage" },
  { key: "users", label: "用户管理", path: "/admin/users", permission: "system:user" },
  { key: "permissions", label: "权限管理", path: "/admin/permissions", permission: "system:role" },
  { key: "smtp", label: "SMTP设置", path: "/admin/smtp", permission: "system:smtp" },
  { key: "settings", label: "系统设置", path: "/admin/settings", permission: "system:settings" },
  { key: "logs", label: "日志查看", path: "/admin/logs", permission: "system:logs" },
  { key: "categories", label: "分类管理", path: "/admin/categories", permission: "plugin:category" },
  { key: "zones", label: "分区管理", path: "/admin/zones", permission: "plugin:zone" },
  { key: "signatures", label: "签名管理", path: "/admin/signatures", permission: "plugin:signature" }
];
