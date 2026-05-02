import {
  del,
  put,
  queryString,
  request,
  type PaginatedResponse,
  type User
} from "@/services/api";

export function getUsers(params: { q?: string; page?: number; page_size?: number } = {}) {
  const query = queryString(params);
  return request<PaginatedResponse<User>>(`/admin/users${query}`);
}

export async function getAllUsers() {
  const data = await getUsers({ page: 1, page_size: 100 });
  return data.items;
}

export function updateUser(userId: number, data: Partial<User>) {
  return put<User>(`/admin/users/${userId}`, data);
}

export function deleteUser(userId: number) {
  return del<{ message: string }>(`/admin/users/${userId}`);
}
