import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AdminSessionProvider } from "@/admin/auth";
import { AdminShell } from "@/admin/AdminShell";
import { adminPageModules } from "@/admin/preload";
import AdminLogin from "@/pages/admin/Login";
import AdminChangePassword from "@/pages/admin/ChangePassword";

const AdminDashboard = lazy(adminPageModules.dashboard);
const ReviewOverview = lazy(adminPageModules.reviewOverview);
const ReviewWorkspace = lazy(adminPageModules.reviewWorkspace);
const ReviewArchive = lazy(adminPageModules.reviewArchive);
const AdminPlugins = lazy(adminPageModules.plugins);
const AdminUsers = lazy(adminPageModules.users);
const AdminPermissions = lazy(adminPageModules.permissions);
const AdminSMTP = lazy(adminPageModules.smtp);
const AdminSettings = lazy(adminPageModules.settings);
const AdminLogs = lazy(adminPageModules.logs);
const AdminCategories = lazy(adminPageModules.categories);
const AdminZones = lazy(adminPageModules.zones);
const AdminSignatures = lazy(adminPageModules.signatures);

function AdminPageFallback() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-32 animate-pulse rounded-lg border bg-card" />
        ))}
      </div>
    </div>
  );
}

function DelayedAdminPageFallback() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(true), 140);
    return () => window.clearTimeout(timer);
  }, []);

  return visible ? <AdminPageFallback /> : null;
}

function withPageSuspense(element: React.ReactNode) {
  return <Suspense fallback={<DelayedAdminPageFallback />}>{element}</Suspense>;
}

function AdminRouteTree() {
  return (
    <Routes>
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin/*" element={<AdminShell />}>
        <Route index element={withPageSuspense(<AdminDashboard />)} />
        <Route path="review/overview" element={withPageSuspense(<ReviewOverview />)} />
        <Route path="review/workspace" element={withPageSuspense(<ReviewWorkspace />)} />
        <Route path="review/archive" element={withPageSuspense(<ReviewArchive />)} />
        <Route path="plugins" element={withPageSuspense(<AdminPlugins />)} />
        <Route path="users" element={withPageSuspense(<AdminUsers />)} />
        <Route path="permissions" element={withPageSuspense(<AdminPermissions />)} />
        <Route path="smtp" element={withPageSuspense(<AdminSMTP />)} />
        <Route path="settings" element={withPageSuspense(<AdminSettings />)} />
        <Route path="logs" element={withPageSuspense(<AdminLogs />)} />
        <Route path="categories" element={withPageSuspense(<AdminCategories />)} />
        <Route path="zones" element={withPageSuspense(<AdminZones />)} />
        <Route path="signatures" element={withPageSuspense(<AdminSignatures />)} />
        <Route path="change-password" element={<AdminChangePassword />} />
      </Route>
    </Routes>
  );
}

export function AdminApp() {
  const queryClient = useMemo(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
        retry: 1
      }
    }
  }), []);

  return (
    <QueryClientProvider client={queryClient}>
      <AdminSessionProvider>
        <AdminRouteTree />
      </AdminSessionProvider>
    </QueryClientProvider>
  );
}
