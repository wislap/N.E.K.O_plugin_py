import { post, request } from "@/services/http/client";
import type { PaginatedResponse } from "@/services/types";
import type {
  ReviewComment,
  ReviewCommentPayload,
  ReviewOverview,
  ReviewSubmission,
  ReviewSubmissionDetail
} from "@/services/admin/types";

export function getReviewOverview() {
  return request<ReviewOverview>("/admin/review/overview");
}

export function getReviewSubmissions(params: {
  q?: string;
  status?: ReviewSubmission["status"];
  decision?: NonNullable<ReviewSubmission["decision"]>;
  severity?: ReviewComment["severity"];
  unresolved_only?: boolean;
  page?: number;
  page_size?: number;
} = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return request<PaginatedResponse<ReviewSubmission>>(`/admin/review/submissions${query ? `?${query}` : ""}`);
}

export function getReviewSubmission(submissionId: number) {
  return request<ReviewSubmissionDetail>(`/admin/review/submissions/${submissionId}`);
}

export function startReviewSubmission(submissionId: number, note?: string) {
  return post<ReviewSubmission>(`/admin/review/submissions/${submissionId}/start`, { note: note || null });
}

export function addReviewComment(caseId: number, payload: ReviewCommentPayload) {
  return post<ReviewComment>(`/admin/review/cases/${caseId}/comments`, payload);
}

export function resolveReviewComment(commentId: number) {
  return post<ReviewComment>(`/admin/review/comments/${commentId}/resolve`);
}

export function reopenReviewComment(commentId: number) {
  return post<ReviewComment>(`/admin/review/comments/${commentId}/reopen`);
}

export function approveReviewCase(caseId: number, payload: { summary?: string | null; force?: boolean } = {}) {
  return post<ReviewSubmission>(`/admin/review/cases/${caseId}/approve`, {
    summary: payload.summary || null,
    force: Boolean(payload.force)
  });
}

export function rejectReviewCase(caseId: number, payload: { summary?: string | null } = {}) {
  return post<ReviewSubmission>(`/admin/review/cases/${caseId}/reject`, {
    summary: payload.summary || null
  });
}
