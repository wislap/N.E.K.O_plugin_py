import { post, request } from "@/services/http/client";
import type { LogStats } from "@/services/types";

export function getLogStats() {
  return request<LogStats>("/admin/logs/stats");
}

export function cleanupLogs(logType = "all") {
  return post<{ message: string; deleted_count: number }>("/admin/logs/cleanup", { log_type: logType });
}

export function getRetentionSettings() {
  return request<Record<string, number>>("/admin/logs/retention-settings");
}
