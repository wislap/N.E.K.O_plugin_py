import { del, post, put, request } from "@/services/http/client";
import type { ZoneAdminItem, ZonePayload } from "./types";

export function getAdminZones() {
  return request<ZoneAdminItem[]>("/admin/zones");
}

export function createZone(data: ZonePayload) {
  return post<ZoneAdminItem & { message: string }>("/admin/zones", data);
}

export function updateZone(zoneId: number, data: Partial<Omit<ZonePayload, "slug">>) {
  return put<ZoneAdminItem & { message: string }>(`/admin/zones/${zoneId}`, data);
}

export function deleteZone(zoneId: number) {
  return del<{ message: string }>(`/admin/zones/${zoneId}`);
}
