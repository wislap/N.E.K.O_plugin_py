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

export interface PluginSubmissionSnapshot {
  id: number;
  submission_id: number;
  revision_number: number;
  repo_url: string;
  repo_owner?: string | null;
  repo_name?: string | null;
  submitted_ref?: string | null;
  resolved_commit?: string | null;
  plugin_name: string;
  plugin_slug: string;
  description?: string | null;
  short_description?: string | null;
  zone_slug?: string | null;
  tags: string[];
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
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  closed_at?: string | null;
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

  async createAndSubmit(data: SubmissionDraftCreateRequest, note?: string) {
    const draft = await this.createDraft(data);
    return this.submit(draft.id, note);
  }
};
