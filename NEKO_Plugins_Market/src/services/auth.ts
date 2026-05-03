import { post, request } from "./http/client";
import type {
  LoginRequest,
  LoginResponse,
  PasswordChangeRequest,
  RegisterRequest,
  ResendVerificationResponse,
  User
} from "./types";

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

  verifyEmail(token: string) {
    return post<User>(`/auth/verify-email?token=${encodeURIComponent(token)}`);
  },

  resendVerificationEmail() {
    return post<ResendVerificationResponse>("/auth/resend-verification-email");
  },

  logout() {
    return post<{ message: string }>("/auth/logout");
  }
};
