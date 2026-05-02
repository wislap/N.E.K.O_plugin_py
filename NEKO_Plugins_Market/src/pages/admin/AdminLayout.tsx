import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Settings,
  Users,
  Shield,
  Mail,
  FileText,
  Puzzle,
  LogOut,
  Menu,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { authApi } from "@/services/api";
import {
  adminApi,
  canAccessAdminPermission,
  hasAnyAdminAccess,
  type UserPermissions,
  type User as ApiUser
} from "@/services/adminApi";

const menuItems = [
  { icon: LayoutDashboard, label: "仪表盘", path: "/admin" },
  { icon: Puzzle, label: "插件审核", path: "/admin/plugins", permission: "plugin:review" },
  { icon: Users, label: "用户管理", path: "/admin/users", permission: "system:user" },
  { icon: Shield, label: "权限管理", path: "/admin/permissions", permission: "system:permission" },
  { icon: Mail, label: "SMTP设置", path: "/admin/smtp", permission: "system:smtp" },
  { icon: Settings, label: "系统设置", path: "/admin/settings", permission: "system:settings" },
  { icon: FileText, label: "日志查看", path: "/admin/logs", permission: "system:logs" },
];

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<ApiUser | null>(null);
  const [permissionState, setPermissionState] = useState<UserPermissions | null>(null);

  useEffect(() => {
    // 检查用户是否已登录
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/admin/login");
      return;
    }

    // 获取当前用户信息
    const fetchUser = async () => {
      try {
        const [userData, permissions] = await Promise.all([
          authApi.getCurrentUser(),
          adminApi.getMyPermissions()
        ]);
        setUser(userData);
        setPermissionState(permissions);
        if (!hasAnyAdminAccess(permissions)) {
          navigate("/");
          return;
        }
        if (userData.must_change_password && location.pathname !== "/admin/change-password") {
          navigate("/admin/change-password", { replace: true });
          return;
        }

        const currentItem = menuItems.find((item) => item.path === location.pathname);
        if (
          currentItem
          && !canAccessAdminPermission(permissions, currentItem.permission)
        ) {
          const firstAllowed = menuItems.find((item) => canAccessAdminPermission(permissions, item.permission));
          navigate(firstAllowed?.path ?? "/", { replace: true });
        }
      } catch (error) {
        navigate("/admin/login");
      }
    };

    fetchUser();
  }, [location.pathname, navigate]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    navigate("/admin/login");
  };

  const visibleMenuItems = user?.must_change_password
    ? []
    : menuItems.filter((item) => canAccessAdminPermission(permissionState, item.permission));

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center border-b px-6">
        <Link to="/admin" className="flex items-center gap-2 font-bold text-xl">
          <span className="text-primary">N.E.K.O</span>
          <span className="text-muted-foreground text-sm">管理后台</span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {visibleMenuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setIsMobileMenuOpen(false)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
              {isActive && <ChevronRight className="ml-auto h-4 w-4" />}
          </Link>
        );
      })}
        {user?.must_change_password && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-600">
            请先修改初始密码
          </div>
        )}
      </nav>

      <div className="border-t p-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-sm font-medium">
              {user?.username?.charAt(0).toUpperCase() || "A"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username || "管理员"}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email || ""}</p>
          </div>
        </div>
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* 移动端菜单 */}
      <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <SheetTrigger asChild className="lg:hidden">
          <Button variant="ghost" size="icon" className="absolute top-4 left-4 z-50">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <SidebarContent />
        </SheetContent>
      </Sheet>

      <div className="flex">
        {/* 桌面端侧边栏 */}
        <aside className="hidden lg:flex w-64 flex-col border-r bg-card min-h-screen sticky top-0">
          <SidebarContent />
        </aside>

        {/* 主内容区 */}
        <main className="flex-1 min-h-screen">
          <header className="h-16 border-b bg-card/50 backdrop-blur flex items-center justify-between px-6 lg:px-8">
            <h1 className="text-lg font-semibold lg:ml-0 ml-12">
                  {location.pathname === "/admin/change-password"
                    ? "修改初始密码"
                    : visibleMenuItems.find((item) => item.path === location.pathname)?.label || "管理后台"}
            </h1>
            <div className="flex items-center gap-4">
              <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
                返回前台
              </Link>
            </div>
          </header>

          <div className="p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
