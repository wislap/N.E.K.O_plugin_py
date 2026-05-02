export type {
  DashboardStats,
  LogStats,
  Plugin,
  Role,
  SMTPSettings,
  SystemSetting,
  User
} from "@/services/api";

export interface UserPermissions {
  user_id: number;
  username: string;
  is_admin: boolean;
  permissions: string[];
  groups: string[];
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  sort_order: number;
  plugin_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ZoneAdminItem {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ServerKeyPair {
  id: number;
  name: string;
  public_key: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  activated_at?: string | null;
  deactivated_at?: string | null;
}

export type CategoryPayload = Omit<Category, "id" | "plugin_count" | "created_at" | "updated_at">;
export type ZonePayload = Omit<ZoneAdminItem, "id" | "created_at" | "updated_at">;
