import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import type { Variants } from "framer-motion";
import { ChevronDown, ChevronRight, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { canAccessAdminPermission } from "@/services/adminApi";
import { adminMenuItems, type AdminMenuItem } from "@/admin/navigation";
import { useAdminSession } from "@/admin/session";

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

interface AdminSidebarProps {
  onNavigate?: () => void;
  onLogout: () => void;
  onPreloadRoute?: (pathname: string) => void;
}

function isItemActive(item: AdminMenuItem, pathname: string) {
  return pathname === item.path || (item.key === "reviewWorkspace" && pathname === "/admin/plugins");
}

function isGroupActive(item: AdminMenuItem, pathname: string) {
  return isItemActive(item, pathname) || Boolean(item.children?.some((child) => isItemActive(child, pathname)));
}

export function AdminSidebar({ onNavigate, onLogout, onPreloadRoute }: AdminSidebarProps) {
  const location = useLocation();
  const prefersReducedMotion = useReducedMotion();
  const { user, permissions } = useAdminSession();
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  const visibleMenuItems = user?.must_change_password
    ? []
    : adminMenuItems.reduce<AdminMenuItem[]>((items, item) => {
      const children = item.children?.filter((child) => canAccessAdminPermission(permissions, child.permission));
      if (!canAccessAdminPermission(permissions, item.permission) && (!children || children.length === 0)) {
        return items;
      }
      items.push({ ...item, children });
      return items;
    }, []);

  const setGroupExpanded = (key: string, expanded: boolean) => {
    setExpandedGroups((current) => ({ ...current, [key]: expanded }));
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center border-b px-6">
        <Link to="/admin" className="flex items-center gap-2 font-bold text-xl" onClick={onNavigate}>
          <span className="text-primary">N.E.K.O</span>
          <span className="text-muted-foreground text-sm">管理后台</span>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        {visibleMenuItems.map((item) => {
          const Icon = item.icon;
          const hasChildren = Boolean(item.children?.length);
          const active = isItemActive(item, location.pathname);
          const groupActive = isGroupActive(item, location.pathname);
          const expanded = hasChildren && (expandedGroups[item.key] || groupActive);

          if (hasChildren) {
            return (
              <div
                key={item.path}
                className="relative space-y-1"
                onMouseEnter={() => {
                  setGroupExpanded(item.key, true);
                  item.children?.forEach((child) => onPreloadRoute?.(child.path));
                }}
                onFocus={() => {
                  setGroupExpanded(item.key, true);
                  item.children?.forEach((child) => onPreloadRoute?.(child.path));
                }}
              >
                <button
                  type="button"
                  onClick={() => setGroupExpanded(item.key, !expanded)}
                  aria-expanded={expanded}
                  className={cn(
                    "relative flex h-10 w-full items-center gap-3 overflow-hidden rounded-lg px-3 text-sm font-medium transition-colors duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    groupActive ? "bg-primary/12 text-primary" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  )}
                >
                  <motion.span
                    aria-hidden="true"
                    initial={false}
                    animate={{ opacity: groupActive ? 1 : 0, scale: groupActive ? 1 : 0.98 }}
                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                    className="absolute inset-0 rounded-lg bg-primary/10"
                  />
                  <span
                    className={cn(
                      "relative flex h-6 w-6 items-center justify-center rounded-md transition-colors duration-200",
                      groupActive ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="relative min-w-0 flex-1 text-left">{item.label}</span>
                  <motion.span
                    animate={{ rotate: expanded ? 180 : 0 }}
                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}
                    className="relative flex"
                  >
                    <ChevronDown className="h-4 w-4" />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {expanded && (
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
                          animate={{ opacity: groupActive ? 1 : 0, scaleY: groupActive ? 1 : 0.5 }}
                          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}
                          className="absolute left-0 top-2 h-7 w-px origin-center rounded-full bg-primary"
                        />
                        <div className="space-y-1 py-1">
                          {item.children?.map((child) => {
                            const ChildIcon = child.icon;
                            const childActive = isItemActive(child, location.pathname);
                            return (
                              <motion.div
                                key={child.path}
                                variants={prefersReducedMotion ? undefined : subItemVariants}
                                transition={{ duration: 0.16, ease: "easeOut" }}
                              >
                                <Link
                                  to={child.path}
                                  onClick={onNavigate}
                                  onFocus={() => onPreloadRoute?.(child.path)}
                                  onMouseEnter={() => onPreloadRoute?.(child.path)}
                                  onPointerDown={() => onPreloadRoute?.(child.path)}
                                  className={cn(
                                    "relative flex h-9 items-center gap-2 overflow-hidden rounded-md px-3 text-sm transition-colors duration-200",
                                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                                    childActive ? "text-primary-foreground" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                                  )}
                                >
                                  <motion.span
                                    aria-hidden="true"
                                    initial={false}
                                    animate={{ opacity: childActive ? 1 : 0, scale: childActive ? 1 : 0.98 }}
                                    transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                                    className="absolute inset-0 rounded-md bg-primary"
                                  />
                                  <ChildIcon className="relative h-4 w-4" />
                                  <span className="relative min-w-0 flex-1 truncate">{child.label}</span>
                                  {childActive && <ChevronRight className="relative h-4 w-4" />}
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
            <Link
              key={item.path}
              to={item.path}
              onClick={onNavigate}
              onFocus={() => onPreloadRoute?.(item.path)}
              onMouseEnter={() => onPreloadRoute?.(item.path)}
              onPointerDown={() => onPreloadRoute?.(item.path)}
              className={cn(
                "relative flex h-10 items-center gap-3 overflow-hidden rounded-lg px-3 text-sm font-medium transition-colors duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                active ? "text-primary-foreground" : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              <motion.span
                aria-hidden="true"
                initial={false}
                animate={{ opacity: active ? 1 : 0, scale: active ? 1 : 0.98 }}
                transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.16, ease: "easeOut" }}
                className="absolute inset-0 rounded-lg bg-primary"
              />
              <Icon className="relative h-4 w-4" />
              <span className="relative min-w-0 flex-1 truncate">{item.label}</span>
              {active && <ChevronRight className="relative ml-auto h-4 w-4" />}
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
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <span className="text-sm font-medium">
              {user?.username?.charAt(0).toUpperCase() || "A"}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.username || "管理员"}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email || ""}</p>
          </div>
        </div>
        <Button variant="outline" className="w-full justify-start gap-2" onClick={onLogout}>
          <LogOut className="h-4 w-4" />
          退出登录
        </Button>
      </div>
    </div>
  );
}
