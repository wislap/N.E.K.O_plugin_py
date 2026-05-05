import type { QueryClient } from "@tanstack/react-query";
import { adminApi } from "@/services/adminApi";
import { dashboardKeys } from "@/admin/dashboardQueries";
import { REVIEW_ARCHIVE_LIST_PARAMS, REVIEW_WORKSPACE_LIST_PARAMS, reviewKeys } from "@/admin/reviewQueries";

export const adminPageModules = {
  dashboard: () => import("@/pages/admin/Dashboard"),
  reviewOverview: () => import("@/pages/admin/ReviewOverview"),
  reviewWorkspace: () => import("@/pages/admin/ReviewWorkspace"),
  reviewArchive: () => import("@/pages/admin/ReviewArchive"),
  users: () => import("@/pages/admin/Users"),
  permissions: () => import("@/pages/admin/Permissions"),
  smtp: () => import("@/pages/admin/SMTP"),
  settings: () => import("@/pages/admin/Settings"),
  logs: () => import("@/pages/admin/Logs"),
  categories: () => import("@/pages/admin/Categories"),
  zones: () => import("@/pages/admin/Zones"),
  signatures: () => import("@/pages/admin/Signatures")
};

function prefetchDashboard(queryClient: QueryClient) {
  return queryClient.prefetchQuery({
    queryKey: dashboardKeys.stats,
    queryFn: adminApi.getDashboardStats,
    staleTime: 120 * 1000
  });
}

function prefetchReviewOverview(queryClient: QueryClient) {
  return queryClient.prefetchQuery({
    queryKey: reviewKeys.overview,
    queryFn: adminApi.getReviewOverview,
    staleTime: 120 * 1000
  });
}

function prefetchReviewWorkspace(queryClient: QueryClient) {
  return queryClient.prefetchQuery({
    queryKey: reviewKeys.submissions(REVIEW_WORKSPACE_LIST_PARAMS),
    queryFn: () => adminApi.getReviewSubmissions(REVIEW_WORKSPACE_LIST_PARAMS),
    staleTime: 60 * 1000
  });
}

function prefetchReviewArchive(queryClient: QueryClient) {
  return queryClient.prefetchQuery({
    queryKey: reviewKeys.submissions(REVIEW_ARCHIVE_LIST_PARAMS),
    queryFn: () => adminApi.getReviewSubmissions(REVIEW_ARCHIVE_LIST_PARAMS),
    staleTime: 60 * 1000
  });
}

export function preloadAdminRouteModule(pathname: string) {
  if (pathname === "/admin") return adminPageModules.dashboard();
  if (pathname === "/admin/review/overview") return adminPageModules.reviewOverview();
  if (pathname === "/admin/review/workspace") return adminPageModules.reviewWorkspace();
  if (pathname === "/admin/review/archive") return adminPageModules.reviewArchive();
  if (pathname === "/admin/users") return adminPageModules.users();
  if (pathname === "/admin/permissions") return adminPageModules.permissions();
  if (pathname === "/admin/smtp") return adminPageModules.smtp();
  if (pathname === "/admin/settings") return adminPageModules.settings();
  if (pathname === "/admin/logs") return adminPageModules.logs();
  if (pathname === "/admin/categories") return adminPageModules.categories();
  if (pathname === "/admin/zones") return adminPageModules.zones();
  if (pathname === "/admin/signatures") return adminPageModules.signatures();
  return Promise.resolve();
}

export function preloadAdminRouteData(pathname: string, queryClient: QueryClient) {
  if (pathname === "/admin") return prefetchDashboard(queryClient);
  if (pathname === "/admin/review/overview") return prefetchReviewOverview(queryClient);
  if (pathname === "/admin/review/workspace") return prefetchReviewWorkspace(queryClient);
  if (pathname === "/admin/review/archive") return prefetchReviewArchive(queryClient);
  return Promise.resolve();
}

export function preloadAdminRoute(pathname: string, queryClient: QueryClient) {
  void preloadAdminRouteModule(pathname);
  void preloadAdminRouteData(pathname, queryClient);
}

export function warmCommonAdminRoutes(queryClient: QueryClient) {
  if (document.visibilityState !== "visible") {
    return;
  }

  void adminPageModules.dashboard();
  void adminPageModules.reviewOverview();
  void adminPageModules.reviewWorkspace();

  const warmRoutes = () => {
    void prefetchDashboard(queryClient);
    void prefetchReviewOverview(queryClient);
    void prefetchReviewWorkspace(queryClient);
  };

  if (window.requestIdleCallback) {
    window.requestIdleCallback(warmRoutes);
  } else {
    window.setTimeout(warmRoutes, 1);
  }
}
