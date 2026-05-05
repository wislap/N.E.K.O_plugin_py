import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/services/adminApi";

export const dashboardKeys = {
  stats: ["admin", "dashboard", "stats"] as const
};

export function useDashboardStats() {
  return useQuery({
    queryKey: dashboardKeys.stats,
    queryFn: adminApi.getDashboardStats,
    staleTime: 30 * 1000
  });
}
