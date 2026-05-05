import { useEffect, useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { canAccessAdminPermission, hasAnyAdminAccess } from "@/services/adminApi";
import { logError } from "@/lib/error-reporting";
import { AdminSidebar } from "@/admin/AdminSidebar";
import { useAdminSession } from "@/admin/session";
import { flatAdminMenuItems, getAdminTitle } from "@/admin/navigation";
import { preloadAdminRoute, preloadAdminRouteData, warmCommonAdminRoutes } from "@/admin/preload";

function AdminLoadingScreen() {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <aside className="hidden min-h-screen w-64 border-r bg-card lg:block" />
        <main className="min-h-screen flex-1">
          <header className="h-16 border-b bg-card/50" />
          <div className="space-y-4 p-6 lg:p-8">
            <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-32 animate-pulse rounded-lg border bg-card" />
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export function AdminShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const session = useAdminSession();

  useEffect(() => {
    if (!session.hasToken) {
      navigate("/admin/login", { replace: true });
    }
  }, [navigate, session.hasToken]);

  useEffect(() => {
    if (!session.isError) {
      return;
    }
    logError(new Error("Admin session load failed"), {
      title: "管理员登录状态检查失败",
      severity: "warn",
      context: { module: "adminShell", action: "loadSession" }
    });
    session.logout();
    navigate("/admin/login", { replace: true });
  }, [navigate, session]);

  useEffect(() => {
    if (!session.user || !session.permissions) {
      return;
    }
    if (!hasAnyAdminAccess(session.permissions)) {
      navigate("/", { replace: true });
      return;
    }
    if (session.user.must_change_password && location.pathname !== "/admin/change-password") {
      navigate("/admin/change-password", { replace: true });
      return;
    }

    const currentItem = flatAdminMenuItems.find((item) => item.path === location.pathname);
    if (currentItem && !canAccessAdminPermission(session.permissions, currentItem.permission)) {
      const firstAllowed = flatAdminMenuItems.find((item) => canAccessAdminPermission(session.permissions, item.permission));
      navigate(firstAllowed?.path ?? "/", { replace: true });
    }
  }, [location.pathname, navigate, session.permissions, session.user]);

  useEffect(() => {
    if (!session.user || !session.permissions || session.user.must_change_password) {
      return;
    }

    warmCommonAdminRoutes(queryClient);
  }, [queryClient, session.permissions, session.user]);

  useEffect(() => {
    if (!session.user || !session.permissions) {
      return;
    }

    void preloadAdminRouteData(location.pathname, queryClient);
  }, [location.pathname, queryClient, session.permissions, session.user]);

  const handleLogout = () => {
    session.logout();
    navigate("/admin/login", { replace: true });
  };

  const handlePreloadRoute = (pathname: string) => {
    preloadAdminRoute(pathname, queryClient);
  };

  if (!session.hasToken || session.isLoading || !session.user || !session.permissions) {
    return <AdminLoadingScreen />;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
        <SheetTrigger asChild className="lg:hidden">
          <Button variant="ghost" size="icon" className="absolute left-4 top-4 z-50">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <AdminSidebar
            onNavigate={() => setIsMobileMenuOpen(false)}
            onLogout={handleLogout}
            onPreloadRoute={handlePreloadRoute}
          />
        </SheetContent>
      </Sheet>

      <div className="flex">
        <aside className="sticky top-0 hidden min-h-screen w-64 flex-col border-r bg-card lg:flex">
          <AdminSidebar onLogout={handleLogout} onPreloadRoute={handlePreloadRoute} />
        </aside>

        <main className="min-h-screen flex-1">
          <header className="flex h-16 items-center justify-between border-b bg-card/50 px-6 backdrop-blur lg:px-8">
            <h1 className="ml-12 text-lg font-semibold lg:ml-0">
              {getAdminTitle(location.pathname)}
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
