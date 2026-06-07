import type { Role as AdminRole } from "@/services/types";

export type {
  DashboardStats,
  LogStats,
  Permission,
  Plugin,
  Role,
  RoleSummary,
  SMTPSettings,
  SystemSetting,
  User
} from "@/services/types";

export interface UserPermissions {
  user_id: number;
  username: string;
  is_admin: boolean;
  is_super_admin?: boolean;
  level: number;
  permissions: string[];
  groups: string[];
  roles: AdminRole[];
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
  submitted_ref?: string | null;
  resolved_commit?: string | null;
  commit_url?: string | null;
  actions_run_url?: string | null;
  artifact_url?: string | null;
  license_name?: string | null;
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
  current_snapshot_id?: number | null;
  current_review_case_id?: number | null;
  current_snapshot?: ReviewSubmissionSnapshot | null;
  review_counts: ReviewCounts;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  closed_at?: string | null;
}

export interface ReviewComment {
  id: number;
  case_id: number;
  author_id: number;
  severity: "critical" | "major" | "minor" | "nitpick";
  target_area: "ownership" | "metadata" | "code" | "security" | "packaging" | "license" | "docs" | "release" | "other";
  target_ref?: string | null;
  body: string;
  is_resolved: boolean;
  resolved_by?: number | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCase {
  id: number;
  submission_id: number;
  snapshot_id: number;
  status: "open" | "closed";
  decision?: ReviewSubmission["decision"];
  opened_by?: number | null;
  closed_by?: number | null;
  decision_summary?: string | null;
  opened_at: string;
  closed_at?: string | null;
  comments: ReviewComment[];
}

export interface ReviewEvent {
  id: number;
  submission_id: number;
  case_id?: number | null;
  actor_id?: number | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ReviewSubmissionDetail extends ReviewSubmission {
  snapshots: ReviewSubmissionSnapshot[];
  review_cases: ReviewCase[];
  events: ReviewEvent[];
}

export interface ReviewCommentPayload {
  severity: ReviewComment["severity"];
  target_area: ReviewComment["target_area"];
  target_ref?: string | null;
  body: string;
}

export type CategoryPayload = Omit<Category, "id" | "plugin_count" | "created_at" | "updated_at">;
export type ZonePayload = Omit<ZoneAdminItem, "id" | "created_at" | "updated_at">;
