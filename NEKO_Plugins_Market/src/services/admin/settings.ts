import { post, put, request, type SMTPSettings, type SystemSetting } from "@/services/api";

export function getSMTPSettings() {
  return request<SMTPSettings>("/admin/settings/smtp");
}

export function updateSMTPSettings(data: SMTPSettings) {
  return put<{ message: string }>("/admin/settings/smtp", data);
}

export function testSMTP(toEmail: string) {
  return post<{ success: boolean; message: string }>("/admin/settings/smtp/test", {
    to_email: toEmail
  });
}

export function getSettings() {
  return request<{ settings: SystemSetting[] }>("/admin/settings");
}

export function initSettings() {
  return post<{ message: string }>("/admin/settings/init");
}

export function updateSetting(key: string, value: string | number | boolean | null) {
  return put<{ message: string; key: string; value?: string | number | boolean | null }>(
    `/admin/settings/${encodeURIComponent(key)}`,
    { value }
  );
}
