import {
  normalizePlugins,
  post,
  request,
  type PaginatedResponse,
  type Plugin
} from "@/services/api";

export async function getAllPlugins() {
  const data = await request<Plugin[] | PaginatedResponse<Plugin>>("/admin/plugins?page_size=100");
  return normalizePlugins(data);
}

export function approvePlugin(pluginId: number, comment?: string) {
  return post<Plugin>(`/admin/plugins/${pluginId}/approve`, { comment: comment?.trim() || null });
}

export function rejectPlugin(pluginId: number, comment?: string) {
  return post<Plugin>(`/admin/plugins/${pluginId}/reject`, { comment: comment?.trim() || null });
}
