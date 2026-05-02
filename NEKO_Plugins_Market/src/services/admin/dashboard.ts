import { request } from "@/services/http/client";
import type { DashboardStats } from "@/services/types";

export function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>("/admin/dashboard/stats");
}
