import {
  del,
  request
} from "@/services/http/client";
import type { PaginatedResponse, Plugin } from "@/services/types";
import { queryString } from "@/services/utils";

export interface AdminPluginListParams extends Record<string, unknown> {
  q?: string;
  status?: string;
  author?: string;
  sort_by?: "created_at" | "download_count" | "likes" | "name";
  sort_order?: "asc" | "desc";
  featured_only?: boolean;
  page?: number;
  page_size?: number;
}

export function getAdminPlugins(params: AdminPluginListParams = {}) {
  const query = queryString(params);
  return request<PaginatedResponse<Plugin>>(`/admin/plugins${query}`);
}

export function deleteAdminPlugin(pluginId: number) {
  return del<{ message: string }>(`/admin/plugins/${pluginId}`);
}
