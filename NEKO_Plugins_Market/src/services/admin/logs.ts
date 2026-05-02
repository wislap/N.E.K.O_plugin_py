import { post, request, type LogStats } from "@/services/api";

export function getLogStats() {
  return request<LogStats>("/admin/logs/stats");
}

export function cleanupLogs(logType = "all") {
  return post<{ message: string; deleted_count: number }>("/admin/logs/cleanup", { log_type: logType });
}

export function getRetentionSettings() {
  return request<Record<string, number>>("/admin/logs/retention-settings");
}
