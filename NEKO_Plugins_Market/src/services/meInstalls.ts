import { post, request } from "./http/client";
import type { UserPluginInstall, UserPluginInstallCreate } from "./types";

export const meInstallsApi = {
  list() {
    return request<UserPluginInstall[]>("/me/installs");
  },

  record(data: UserPluginInstallCreate) {
    return post<UserPluginInstall>("/me/installs", data);
  },
};
