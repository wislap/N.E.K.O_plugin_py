import { del, post, put, request } from "@/services/http/client";
import type { Category, CategoryPayload } from "./types";

export function getCategories() {
  return request<Category[]>("/admin/categories");
}

export function createCategory(data: CategoryPayload) {
  return post<Category>("/admin/categories", data);
}

export function updateCategory(categoryId: number, data: Partial<CategoryPayload>) {
  return put<Category>(`/admin/categories/${categoryId}`, data);
}

export function deleteCategory(categoryId: number) {
  return del<{ message: string }>(`/admin/categories/${categoryId}`);
}
