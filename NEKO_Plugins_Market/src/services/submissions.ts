import { post, request } from "./http/client";
import type { PaginatedResponse } from "./types";

export interface SubmissionDraftCreateRequest {
  repo_url: string;
  plugin_name: string;
  plugin_slug: string;
  description?: string;
  short_description?: string;
  zone_slug?: string;
  tags?: string[];
  submitted_ref?: string;
  metadata?: Record<string, unknown>;
}

export interface SubmissionRevisionRequest {
  repo_url?: string;
  plugin_name?: string;
  plugin_slug?: string;
  description?: string | null;
  short_description?: string | null;
  zone_slug?: string | null;
  tags?: string[];
  submitted_ref?: string | null;
  resolved_commit?: string | null;
  commit_url?: string | null;
  actions_run_url?: string | null;
  artifact_url?: string | null;
  license_name?: string | null;
  metadata?: Record<string, unknown>;
  note?: string | null;
}

export interface PluginSubmissionSnapshot {
  id: number;
  submission_id: number;
  revision_number: number;
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
  description?: string | null;
  short_description?: string | null;
  zone_slug?: string | null;
  tags: string[];
  created_at: string;
}

export interface SubmissionReviewCounts {
  critical: number;
  major: number;
  minor: number;
  nitpick: number;
  unresolved: number;
}

export interface SubmissionReviewComment {
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

export interface SubmissionReviewCase {
  id: number;
  submission_id: number;
  snapshot_id: number;
  status: "open" | "closed";
  decision?: PluginSubmission["decision"];
  opened_by?: number | null;
  closed_by?: number | null;
  decision_summary?: string | null;
  opened_at: string;
  closed_at?: string | null;
  comments: SubmissionReviewComment[];
}

export interface SubmissionReviewEvent {
  id: number;
  submission_id: number;
  case_id?: number | null;
  actor_id?: number | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface PluginSubmission {
  id: number;
  plugin_id?: number | null;
  author_id: number;
  status: "draft" | "submitted" | "in_review" | "closed";
  decision?: "approved" | "rejected" | "canceled" | "superseded" | null;
  current_snapshot_id?: number | null;
  current_review_case_id?: number | null;
  current_snapshot?: PluginSubmissionSnapshot | null;
  current_review_case?: SubmissionReviewCase | null;
  review_counts: SubmissionReviewCounts;
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  closed_at?: string | null;
}

export interface PluginSubmissionDetail extends PluginSubmission {
  snapshots: PluginSubmissionSnapshot[];
  review_cases: SubmissionReviewCase[];
  events: SubmissionReviewEvent[];
}

export const submissionsApi = {
  createDraft(data: SubmissionDraftCreateRequest) {
    return post<PluginSubmission>("/review/submissions/drafts", data);
  },

  submit(submissionId: number, note?: string) {
    return post<PluginSubmission>(`/review/submissions/${submissionId}/submit`, { note: note || null });
  },

  mine() {
    return request<PaginatedResponse<PluginSubmission>>("/review/submissions/mine?page_size=100");
  },

  detail(submissionId: number) {
    return request<PluginSubmissionDetail>(`/review/submissions/${submissionId}`);
  },

  createRevision(submissionId: number, data: SubmissionRevisionRequest) {
    return post<PluginSubmissionDetail>(`/review/submissions/${submissionId}/revision`, data);
  },

  async createAndSubmit(data: SubmissionDraftCreateRequest, note?: string) {
    const draft = await this.createDraft(data);
    return this.submit(draft.id, note);
  }
};
