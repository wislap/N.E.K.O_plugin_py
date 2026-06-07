import { Link } from "react-router-dom";
import {
  Users,
  Puzzle,
  CheckCircle,
  Clock,
  TrendingUp,
  Activity,
  Shield,
  AlertTriangle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  canAccessAdminPermission,
} from "@/services/adminApi";
import { adminModules } from "@/lib/adminModules";
import type { AdminModule } from "@/lib/adminModules";
import { useAdminSession } from "@/admin/session";
import { useDashboardStats } from "@/admin/dashboardQueries";

function flattenModules(modules: AdminModule[]): AdminModule[] {
  return modules.flatMap((module) => [module, ...(module.children ? flattenModules(module.children) : [])]);
}

const adminModuleByKey = Object.fromEntries(
  flattenModules(adminModules).map((module) => [module.key, module])
);

export default function AdminDashboard() {
  const { permissions } = useAdminSession();
  const { data, isLoading } = useDashboardStats();
  const stats = data ?? {
    totalUsers: 0,
    totalPlugins: 0,
    pendingPlugins: 0,
    approvedPlugins: 0,
    rejectedPlugins: 0,
    recentUsers: 0,
    recentPlugins: 0
  };

  const canReviewPlugins = canAccessAdminPermission(permissions, "plugin:review");
  const canManageUsers = canAccessAdminPermission(permissions, "system:user");
  const canManagePermissions = canAccessAdminPermission(permissions, "system:role");
  const canManageSmtp = canAccessAdminPermission(permissions, "system:smtp");
  const canManageSettings = canAccessAdminPermission(permissions, "system:settings");
  const canViewLogs = canAccessAdminPermission(permissions, "system:logs");
  const canManageCategories = canAccessAdminPermission(permissions, "plugin:category");
  const canManageZones = canAccessAdminPermission(permissions, "plugin:zone");
  const canManageSignatures = canAccessAdminPermission(permissions, "plugin:signature");

  const statCards = [
    {
      title: "总用户数",
      value: stats.totalUsers,
      icon: Users,
      trend: `+${stats.recentUsers} 本周新增`,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
      visible: canManageUsers
    },
    {
      title: "插件总数",
      value: stats.totalPlugins,
      icon: Puzzle,
      trend: `+${stats.recentPlugins} 本周新增`,
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
      visible: canReviewPlugins
    },
    {
      title: "待审核插件",
      value: stats.pendingPlugins,
      icon: Clock,
      trend: "需要处理",
      color: "text-yellow-500",
      bgColor: "bg-yellow-500/10",
      visible: canReviewPlugins
    },
    {
      title: "已通过插件",
      value: stats.approvedPlugins,
      icon: CheckCircle,
      trend: "已上线",
      color: "text-green-500",
      bgColor: "bg-green-500/10",
      visible: canReviewPlugins
    }
  ].filter((card) => card.visible);

  const quickActions = [
    {
      title: adminModuleByKey.pluginReview.label,
      href: adminModuleByKey.reviewWorkspace.path,
      value: `${stats.pendingPlugins} 个待审`,
      icon: Clock,
      color: "text-yellow-500",
      visible: canReviewPlugins
    },
    {
      title: adminModuleByKey.users.label,
      href: adminModuleByKey.users.path,
      value: `${stats.totalUsers} 个用户`,
      icon: Users,
      color: "text-blue-500",
      visible: canManageUsers
    },
    {
      title: adminModuleByKey.permissions.label,
      href: adminModuleByKey.permissions.path,
      value: "角色与权限",
      icon: Shield,
      color: "text-primary",
      visible: canManagePermissions
    },
    {
      title: adminModuleByKey.logs.label,
      href: adminModuleByKey.logs.path,
      value: "实时监控",
      icon: AlertTriangle,
      color: "text-orange-500",
      visible: canViewLogs
    }
  ].filter((action) => action.visible);

  const statusItems = [
    { title: "插件审核服务", visible: canReviewPlugins },
    { title: "权限系统", visible: canManagePermissions },
    { title: "邮件服务", visible: canManageSmtp },
    { title: "系统配置", visible: canManageSettings },
    { title: "日志服务", visible: canViewLogs },
    { title: "分类配置", visible: canManageCategories },
    { title: "分区配置", visible: canManageZones },
    { title: "签名服务", visible: canManageSignatures }
  ].filter((item) => item.visible);

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      {statCards.length > 0 && (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {card.title}
                </CardTitle>
                <div className={`${card.bgColor} p-2 rounded-lg`}>
                  <Icon className={`h-4 w-4 ${card.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {isLoading ? "-" : card.value}
                </div>
                <p className="text-xs text-muted-foreground">
                  {card.trend}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>
      )}

      {/* 快捷操作 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {quickActions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              快捷操作
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.href}
                  to={action.href}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${action.color}`} />
                    <span>{action.title}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {action.value}
                  </span>
                </Link>
              );
            })}
          </CardContent>
        </Card>
        )}

        {statusItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              系统状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {statusItems.map((item) => (
              <div key={item.title} className="flex items-center justify-between">
                <span className="text-sm">{item.title}</span>
                <span className="flex items-center gap-1 text-sm text-green-500">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  可用
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
        )}

        {canReviewPlugins && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              插件统计
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>已通过</span>
                <span className="text-muted-foreground">
                  {stats.approvedPlugins}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{
                    width: `${stats.totalPlugins > 0 ? (stats.approvedPlugins / stats.totalPlugins) * 100 : 0}%`
                  }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>待审核</span>
                <span className="text-muted-foreground">
                  {stats.pendingPlugins}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-500 rounded-full"
                  style={{
                    width: `${stats.totalPlugins > 0 ? (stats.pendingPlugins / stats.totalPlugins) * 100 : 0}%`
                  }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>已拒绝</span>
                <span className="text-muted-foreground">
                  {stats.rejectedPlugins}
                </span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-red-500 rounded-full"
                  style={{
                    width: `${stats.totalPlugins > 0 ? (stats.rejectedPlugins / stats.totalPlugins) * 100 : 0}%`
                  }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        )}
      </div>
    </div>
  );
}
