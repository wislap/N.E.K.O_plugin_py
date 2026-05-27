import { post, request } from "./http/client";
import type {
  LoginRequest,
  LoginResponse,
  PasswordChangeRequest,
  PublicResendVerificationRequest,
  RegisterResponse,
  RegisterRequest,
  ResendVerificationResponse,
  User
} from "./types";

export const authApi = {
  register(data: RegisterRequest) {
    return post<RegisterResponse>("/auth/register", data);
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

  resendVerificationEmailPublic(data: PublicResendVerificationRequest) {
    return post<ResendVerificationResponse>("/auth/resend-verification-email/public", data);
  },

  logout() {
    const refreshToken = localStorage.getItem("refreshToken");
    return post<{ message: string }>(
      "/auth/logout",
      refreshToken ? { refresh_token: refreshToken } : undefined,
    );
  }
};
