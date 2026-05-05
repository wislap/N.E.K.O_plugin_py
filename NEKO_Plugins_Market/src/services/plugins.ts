import { post, request } from "./http/client";
import { toMarketPlugin } from "./mappers";
import type { PaginatedResponse, Plugin, PluginQuery } from "./types";
import { queryString } from "./utils";

export const pluginsApi = {
  async list(params: PluginQuery = {}) {
    const data = await request<PaginatedResponse<Plugin>>(`/plugins${queryString(params)}`);
    return {
      ...data,
      items: data.items.map(toMarketPlugin)
    };
  },

  async featured(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/featured?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async popular(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/popular?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async newest(limit = 6) {
    const data = await request<Plugin[]>(`/plugins/newest?limit=${limit}`);
    return data.map(toMarketPlugin);
  },

  async getById(id: string) {
    const data = await request<Plugin>(`/plugins/${id}`);
    return toMarketPlugin(data);
  },

  mine() {
    return request<Plugin[]>("/plugins/mine");
  },

  recordDownload(pluginId: string) {
    return post<{ message: string; success: boolean }>(`/plugins/${pluginId}/download`);
  }
};
