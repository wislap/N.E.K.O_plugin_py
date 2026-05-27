import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/services/auth";
import { adminApi } from "@/services/adminApi";
import { AdminSessionContext, type AdminSession } from "@/admin/session";

function getStoredToken() {
  return localStorage.getItem("token");
}

function clearStoredSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("currentUser");
  window.dispatchEvent(new Event("auth:changed"));
}

export function AdminSessionProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(getStoredToken);
  const hasToken = Boolean(token);

  useEffect(() => {
    const syncToken = () => setToken(getStoredToken());

    window.addEventListener("auth:changed", syncToken);
    window.addEventListener("storage", syncToken);
    return () => {
      window.removeEventListener("auth:changed", syncToken);
      window.removeEventListener("storage", syncToken);
    };
  }, []);

  const userQuery = useQuery({
    queryKey: ["admin", "currentUser", token],
    queryFn: authApi.getCurrentUser,
    enabled: hasToken,
    staleTime: 5 * 60 * 1000,
    retry: false
  });

  const permissionsQuery = useQuery({
    queryKey: ["admin", "permissions", "me", token],
    queryFn: adminApi.getMyPermissions,
    enabled: hasToken,
    staleTime: 5 * 60 * 1000,
    retry: false
  });

  const value = useMemo<AdminSession>(() => ({
    user: userQuery.data ?? null,
    permissions: permissionsQuery.data ?? null,
    hasToken,
    isLoading: hasToken && (userQuery.isLoading || permissionsQuery.isLoading),
    isError: userQuery.isError || permissionsQuery.isError,
    logout: () => {
      void authApi.logout().catch(() => undefined);
      clearStoredSession();
      queryClient.removeQueries({ queryKey: ["admin"] });
    }
  }), [
    hasToken,
    permissionsQuery.data,
    permissionsQuery.isError,
    permissionsQuery.isLoading,
    queryClient,
    userQuery.data,
    userQuery.isError,
    userQuery.isLoading
  ]);

  return (
    <AdminSessionContext.Provider value={value}>
      {children}
    </AdminSessionContext.Provider>
  );
}
