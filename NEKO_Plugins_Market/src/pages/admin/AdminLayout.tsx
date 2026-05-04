import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  Archive,
  BarChart3,
  LayoutDashboard,
  Settings,
  Users,
  Shield,
  Mail,
  FileText,
  Puzzle,
  FolderTree,
  Layers3,
  KeyRound,
  LogOut,
  Menu,
  ClipboardList,
  ChevronDown,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { adminModules, type AdminModule } from "@/lib/adminModules";
import { cn } from "@/lib/utils";
import { authApi } from "@/services/auth";
import {
  adminApi,
  canAccessAdminPermission,
  hasAnyAdminAccess,
  type UserPermissions,
  type User as ApiUser
} from "@/services/adminApi";
import { logError } from "@/lib/error-reporting";

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

type AdminMenuItem = Omit<AdminModule, "children"> & {
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

function flattenMenu(items: AdminMenuItem[]): AdminMenuItem[] {
  return items.flatMap((item) => [item, ...(item.children ? flattenMenu(item.children) : [])]);
}

const menuItems = withMenuIcons(adminModules);
const flatMenuItems = flattenMenu(menuItems);

const groupPanelVariants: Variants = {
  collapsed: {
    height: 0,
    opacity: 0,
    transition: {
      height: { duration: 0.18, ease: "easeInOut" },
      opacity: { duration: 0.12 }
    }
  },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: {
      height: { duration: 0.24, ease: "easeOut" },
      opacity: { duration: 0.18, delay: 0.04 },
      staggerChildren: 0.035,
      delayChildren: 0.04
    }
  }
};

const subItemVariants: Variants = {
  collapsed: { opacity: 0, x: -8 },
  expanded: { opacity: 1, x: 0 }
};

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [user, setUser] = useState<ApiUser | null>(null);
  const [permissionState, setPermissionState] = useState<UserPermissions | null>(null);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    const activeGroup = menuItems.find((item) => (
      item.children?.some((child) => location.pathname === child.path)
      || (item.key === "pluginReview" && location.pathname === "/admin/plugins")
    ));
    if (activeGroup) {
      setExpandedGroups((current) => ({ ...current, [activeGroup.key]: true }));
    }
  }, [location.pathname]);

  useEffect(() => {
    let isMounted = true;
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/admin/login");
      return;
    }

    const fetchUser = async () => {
      try {
        const [userData, permissions] = await Promise.all([
          authApi.getCurrentUser(),
          adminApi.getMyPermissions()
        ]);
        if (!isMounted) {
          return;
        }
        setUser(userData);
        setPermissionState(permissions);
        setAuthReady(true);
        if (!hasAnyAdminAccess(permissions)) {
          navigate("/");
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }
        logError(error, {
          title: "管理员登录状态检查失败",
          severity: "warn",
          context: {
            module: "adminLayout",
            action: "fetchUser"
          }
        });
        navigate("/admin/login");
      }
    };

    fetchUser();
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  useEffect(() => {
    if (!authReady || !user || !permissionState) {
      return;
    }
    if (user.must_change_password && location.pathname !== "/admin/change-password") {
      navigate("/admin/change-password", { replace: true });
      return;
    }

    const currentItem = flatMenuItems.find((item) => item.path === location.pathname);
    if (
      currentItem
      && !canAccessAdminPermission(permissionState, currentItem.permission)
    ) {
      const firstAllowed = flatMenuItems.find((item) => canAccessAdminPermission(permissionState, item.permission));
      navigate(firstAllowed?.path ?? "/", { replace: true });
    }
  }, [authReady, location.pathname, navigate, permissionState, user]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    navigate("/admin/login");
  };

  const visibleMenuItems: AdminMenuItem[] = user?.must_change_password
    ? []
    : menuItems.reduce<AdminMenuItem[]>((items, item) => {
      const children = item.children?.filter((child) => canAccessAdminPermission(permissionState, child.permission));
      if (!canAccessAdminPermission(permissionState, item.permission) && (!children || children.length === 0)) {
        return items;
      }
      items.push({ ...item, children });
      return items;
    }, []);

  const activeTitle = flatMenuItems.find((item) => item.path === location.pathname)?.label
    ?? (location.pathname === "/admin/plugins" ? "工作区" : "管理后台");

  const isItemActive = (item: AdminMenuItem) => (
    location.pathname === item.path
    || (item.key === "reviewWorkspace" && location.pathname === "/admin/plugins")
  );

  const isGroupActive = (item: AdminMenuItem) => (
    isItemActive(item)
    || Boolean(item.children?.some((child) => isItemActive(child)))
  );

  const setGroupExpanded = (key: string, expanded: boolean) => {
    setExpandedGroups((current) => ({ ...current, [key]: expanded }));
  };

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
          const hasChildren = Boolean(item.children?.length);
          const isActive = isItemActive(item);
          const isExpanded = hasChildren && (expandedGroups[item.key] || isGroupActive(item));

          if (hasChildren) {
            return (
              <div
                key={item.path}
                className="group/nav-section relative space-y-1"
                onMouseEnter={() => setGroupExpanded(item.key, true)}
              >
                <button
                  type="button"
                  onClick={() => setGroupExpanded(item.key, !isExpanded)}
                  aria-expanded={isExpanded}
                  className={cn(
                    "relative flex h-10 w-full items-center gap-3 overflow-hidden rounded-lg px-3 text-sm font-medium transition-colors duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isGroupActive(item)
                      ? "bg-primary/12 text-primary"
                      : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  )}
                >
                  <motion.span
                    aria-hidden="true"
                    initial={false}
                    animate={{
                      opacity: isGroupActive(item) ? 1 : 0,
                      scale: isGroupActive(item) ? 1 : 0.98
                    }}
                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                    className="absolute inset-0 rounded-lg bg-primary/10"
                  />
                  <span
                    className={cn(
                      "relative flex h-6 w-6 items-center justify-center rounded-md transition-colors duration-200",
                      isGroupActive(item) ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1 text-left">{item.label}</span>
                  <motion.span
                    animate={{ rotate: isExpanded ? 180 : 0 }}
                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}
                    className="relative flex"
                  >
                    <ChevronDown className="h-4 w-4" />
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      key={`${item.key}-children`}
                      initial="collapsed"
                      animate="expanded"
                      exit="collapsed"
                      variants={prefersReducedMotion ? undefined : groupPanelVariants}
                      className="overflow-hidden"
                    >
                      <div className="relative ml-5 mt-1.5 pl-4">
                        <span className="absolute left-0 top-1 bottom-1 w-px rounded-full bg-border" />
                        <motion.span
                          aria-hidden="true"
                          initial={false}
                          animate={{
                            opacity: isGroupActive(item) ? 1 : 0,
                            scaleY: isGroupActive(item) ? 1 : 0.5
                          }}
                          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}
                          className="absolute left-0 top-2 h-7 w-px origin-center rounded-full bg-primary"
                        />
                        <div className="space-y-1 py-1">
                          {item.children?.map((child) => {
                            const ChildIcon = child.icon;
                            const childActive = isItemActive(child);
                            return (
                              <motion.div
                                key={child.path}
                                variants={prefersReducedMotion ? undefined : subItemVariants}
                                transition={{ duration: 0.16, ease: "easeOut" }}
                              >
                                <Link
                                  to={child.path}
                                  onClick={() => setIsMobileMenuOpen(false)}
                                  className={cn(
                                    "relative flex h-9 items-center gap-2 overflow-hidden rounded-md px-3 text-sm transition-colors duration-200",
                                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                                    childActive
                                      ? "text-primary-foreground"
                                      : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                                  )}
                                >
                                  <motion.span
                                    aria-hidden="true"
                                    initial={false}
                                    animate={{
                                      opacity: childActive ? 1 : 0,
                                      scale: childActive ? 1 : 0.98
                                    }}
                                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                                    className="absolute inset-0 rounded-md bg-primary"
                                  />
                                  <ChildIcon className="relative h-4 w-4" />
                                  <span className="relative min-w-0 flex-1 truncate">{child.label}</span>
                                  {childActive && (
                                    <motion.span
                                      initial={prefersReducedMotion ? false : { opacity: 0, x: -4 }}
                                      animate={{ opacity: 1, x: 0 }}
                                      exit={{ opacity: 0, x: -4 }}
                                      className="relative"
                                    >
                                      <ChevronRight className="h-4 w-4" />
                                    </motion.span>
                                  )}
                                </Link>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          }

          return (
            <motion.div key={item.path} layout>
              <Link
              key={item.path}
              to={item.path}
              onClick={() => setIsMobileMenuOpen(false)}
              className={cn(
                "relative flex h-10 items-center gap-3 overflow-hidden rounded-lg px-3 text-sm font-medium transition-colors duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                isActive ? "text-primary-foreground" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
              >
                <motion.span
                  aria-hidden="true"
                  initial={false}
                  animate={{
                    opacity: isActive ? 1 : 0,
                    scale: isActive ? 1 : 0.98
                  }}
                  transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                  className="absolute inset-0 rounded-lg bg-primary"
                />
                <Icon className="relative h-4 w-4" />
                <span className="relative min-w-0 flex-1 truncate">{item.label}</span>
                {isActive && <ChevronRight className="relative ml-auto h-4 w-4" />}
              </Link>
            </motion.div>
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
                    : activeTitle}
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
