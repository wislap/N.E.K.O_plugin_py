import { post, request } from "./http/client";
import type { PluginVersion, PluginVersionCreateRequest } from "./types";

export const versionsApi = {
  list(pluginId: number) {
    return request<PluginVersion[]>(`/plugins/${pluginId}/versions`);
  },

  latest(pluginId: number) {
    return request<PluginVersion>(`/plugins/${pluginId}/versions/latest`);
  },

  create(pluginId: number, data: PluginVersionCreateRequest) {
    return post<PluginVersion>(`/plugins/${pluginId}/versions`, data);
  }
};
