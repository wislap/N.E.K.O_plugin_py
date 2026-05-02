import { post, request } from "./http/client";
import type { Notification } from "./types";

export const notificationsApi = {
  list(limit = 20) {
    return request<Notification[]>(`/notifications?limit=${limit}`);
  },

  unreadCount() {
    return request<{ count: number }>("/notifications/unread-count");
  },

  markRead(notificationId: number) {
    return post<Notification>(`/notifications/${notificationId}/read`);
  },

  markAllRead() {
    return post<{ message: string; success: boolean }>("/notifications/read-all");
  }
};
