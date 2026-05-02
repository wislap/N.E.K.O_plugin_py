import type { Zone } from "@/types";
import { request } from "./http/client";

export const zonesApi = {
  list() {
    return request<Zone[]>("/zones");
  }
};
