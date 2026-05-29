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

  /** 返回未经 mapper 转换的 raw plugin 对象（保留 author_id / latest_version 等服务端字段）。
   *  用于需要权限判断或读取版本元数据的页面（如 PluginDetail 版本 tab）。
   */
  async getRawById(id: string) {
    return request<Plugin>(`/plugins/${id}`);
  },

  mine() {
    return request<Plugin[]>("/plugins/mine");
  },

  recordDownload(pluginId: string) {
    return post<{ message: string; success: boolean }>(`/plugins/${pluginId}/download`);
  },

  setLike(pluginId: string, liked: boolean) {
    return request<{ plugin_id: number; liked: boolean; likes: number }>(
      `/plugins/${pluginId}/like?liked=${liked ? "true" : "false"}`,
      { method: "PUT" }
    );
  }
};
