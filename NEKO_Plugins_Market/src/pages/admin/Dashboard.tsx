import { useEffect, useState } from "react";
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
import { adminApi } from "@/services/adminApi";

interface DashboardStats {
  totalUsers: number;
  totalPlugins: number;
  pendingPlugins: number;
  approvedPlugins: number;
  rejectedPlugins: number;
  recentUsers: number;
  recentPlugins: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalUsers: 0,
    totalPlugins: 0,
    pendingPlugins: 0,
    approvedPlugins: 0,
    rejectedPlugins: 0,
    recentUsers: 0,
    recentPlugins: 0
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setIsLoading(true);
      const data = await adminApi.getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error("获取统计数据失败:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const statCards = [
    {
      title: "总用户数",
      value: stats.totalUsers,
      icon: Users,
      trend: `+${stats.recentUsers} 本周新增`,
      color: "text-blue-500",
      bgColor: "bg-blue-500/10"
    },
    {
      title: "插件总数",
      value: stats.totalPlugins,
      icon: Puzzle,
      trend: `+${stats.recentPlugins} 本周新增`,
      color: "text-purple-500",
      bgColor: "bg-purple-500/10"
    },
    {
      title: "待审核插件",
      value: stats.pendingPlugins,
      icon: Clock,
      trend: "需要处理",
      color: "text-yellow-500",
      bgColor: "bg-yellow-500/10"
    },
    {
      title: "已通过插件",
      value: stats.approvedPlugins,
      icon: CheckCircle,
      trend: "已上线",
      color: "text-green-500",
      bgColor: "bg-green-500/10"
    }
  ];

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
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

      {/* 快捷操作 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              快捷操作
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <a
              href="#/admin/plugins"
              className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-yellow-500" />
                <span>审核待处理插件</span>
              </div>
              <span className="text-sm text-muted-foreground">
                {stats.pendingPlugins} 个待审
              </span>
            </a>
            <a
              href="#/admin/users"
              className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <Users className="h-4 w-4 text-blue-500" />
                <span>管理用户</span>
              </div>
              <span className="text-sm text-muted-foreground">
                {stats.totalUsers} 个用户
              </span>
            </a>
            <a
              href="#/admin/logs"
              className="flex items-center justify-between p-3 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                <span>查看系统日志</span>
              </div>
              <span className="text-sm text-muted-foreground">
                实时监控
              </span>
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              系统状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">AI 审核服务</span>
              <span className="flex items-center gap-1 text-sm text-green-500">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                正常运行
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">签名服务</span>
              <span className="flex items-center gap-1 text-sm text-green-500">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                正常运行
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">邮件服务</span>
              <span className="flex items-center gap-1 text-sm text-green-500">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                正常运行
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">GitHub API</span>
              <span className="flex items-center gap-1 text-sm text-green-500">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                连接正常
              </span>
            </div>
          </CardContent>
        </Card>

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
      </div>
    </div>
  );
}
