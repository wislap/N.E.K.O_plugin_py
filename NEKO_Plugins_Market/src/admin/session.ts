import { createContext, useContext } from "react";
import type { User as ApiUser, UserPermissions } from "@/services/adminApi";

export interface AdminSession {
  user: ApiUser | null;
  permissions: UserPermissions | null;
  hasToken: boolean;
  isLoading: boolean;
  isError: boolean;
  logout: () => void;
}

export const AdminSessionContext = createContext<AdminSession | null>(null);

export function useAdminSession() {
  const session = useContext(AdminSessionContext);
  if (!session) {
    throw new Error("useAdminSession must be used within AdminSessionProvider");
  }
  return session;
}
