import { request, type DashboardStats } from "@/services/api";

export function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>("/admin/dashboard/stats");
}
