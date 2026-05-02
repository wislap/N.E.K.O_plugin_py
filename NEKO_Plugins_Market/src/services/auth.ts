import { post, request } from "./http/client";
import type { LoginRequest, LoginResponse, PasswordChangeRequest, RegisterRequest, User } from "./types";

export const authApi = {
  register(data: RegisterRequest) {
    return post<LoginResponse>("/auth/register", data);
  },

  debugLogin() {
    return post<LoginResponse>("/auth/debug-login");
  },

  login(credentials: LoginRequest) {
    return post<LoginResponse>("/auth/login", credentials);
  },

  getCurrentUser() {
    return request<User>("/auth/me");
  },

  changePassword(data: PasswordChangeRequest) {
    return post<User>("/auth/change-password", data);
  },

  logout() {
    return post<{ message: string }>("/auth/logout");
  }
};
