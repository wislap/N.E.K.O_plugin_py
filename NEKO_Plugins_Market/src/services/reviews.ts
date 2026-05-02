import { post, request } from "./http/client";
import { toMarketReview } from "./mappers";
import type { PaginatedResponse, ReviewCreateRequest, ReviewDto } from "./types";

export const reviewsApi = {
  async list(pluginId: string) {
    const data = await request<PaginatedResponse<ReviewDto>>(`/plugins/${pluginId}/reviews`);

    return {
      ...data,
      items: data.items.map(toMarketReview)
    };
  },

  async create(pluginId: string, data: ReviewCreateRequest) {
    const review = await post<ReviewDto>(`/plugins/${pluginId}/reviews`, data);
    return toMarketReview(review);
  }
};
