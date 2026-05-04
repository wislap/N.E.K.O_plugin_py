import { request } from "@/services/http/client";
import type { PaginatedResponse } from "@/services/types";
import type { ReviewOverview, ReviewSubmission } from "@/services/admin/types";

export function getReviewOverview() {
  return request<ReviewOverview>("/admin/review/overview");
}

export function getReviewSubmissions(params: {
  status?: ReviewSubmission["status"];
  decision?: NonNullable<ReviewSubmission["decision"]>;
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
