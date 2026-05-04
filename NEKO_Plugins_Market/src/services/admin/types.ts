export type {
  DashboardStats,
  LogStats,
  Plugin,
  Role,
  SMTPSettings,
  SystemSetting,
  User
} from "@/services/types";

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

export interface ReviewOverview {
  draft: number;
  submitted: number;
  in_review: number;
  closed: number;
  approved: number;
  rejected: number;
  unresolved_critical: number;
  unresolved_major: number;
}

export interface ReviewSubmissionSnapshot {
  id: number;
  repo_url: string;
  repo_owner?: string | null;
  repo_name?: string | null;
  plugin_name: string;
  plugin_slug: string;
  short_description?: string | null;
  zone_slug?: string | null;
  tags: string[];
  created_at: string;
}

export interface ReviewCounts {
  critical: number;
  major: number;
  minor: number;
  nitpick: number;
  unresolved: number;
}

export interface ReviewSubmission {
  id: number;
  plugin_id?: number | null;
  author_id: number;
  status: "draft" | "submitted" | "in_review" | "closed";
  decision?: "approved" | "rejected" | "canceled" | "superseded" | null;
  current_snapshot?: ReviewSubmissionSnapshot | null;
  review_counts: ReviewCounts;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  closed_at?: string | null;
}

export type CategoryPayload = Omit<Category, "id" | "plugin_count" | "created_at" | "updated_at">;
export type ZonePayload = Omit<ZoneAdminItem, "id" | "created_at" | "updated_at">;
