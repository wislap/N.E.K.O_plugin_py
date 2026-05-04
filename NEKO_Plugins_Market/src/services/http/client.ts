import { logError } from "@/lib/error-reporting";
import type { RequestBody } from "@/services/types";
import { ApiError, parseErrorResponse } from "./errors";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const REQUEST_ID_HEADER = "X-Request-ID";

function getToken() {
  return localStorage.getItem("token");
}

function createRequestId() {
  return `web-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("currentUser");
  window.dispatchEvent(new Event("auth:changed"));
}

async function refreshAccessToken(requestId: string) {
  const refreshToken = localStorage.getItem("refreshToken");
  if (!refreshToken) {
    clearSession();
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        [REQUEST_ID_HEADER]: requestId
      },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (!response.ok) {
      clearSession();
      return null;
    }

    const data = await response.json() as { access_token?: string };
    if (!data.access_token) {
      clearSession();
      return null;
    }

    localStorage.setItem("token", data.access_token);
    window.dispatchEvent(new Event("auth:changed"));
    return data.access_token;
  } catch {
    clearSession();
    return null;
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  const method = options.method ?? "GET";
  const requestId = headers.get(REQUEST_ID_HEADER) ?? createRequestId();
  headers.set(REQUEST_ID_HEADER, requestId);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers
    });
  } catch (error) {
    const networkError = new ApiError(
      error instanceof Error ? error.message : "网络请求失败，请检查后端服务是否已启动。",
      {
        status: 0,
        path,
        method,
        requestId,
        detail: error
      }
    );
    logError(networkError, {
      severity: "error",
      title: "网络请求失败",
      context: { method, path, apiBaseUrl: API_BASE_URL, requestId }
    });
    throw networkError;
  }

  const responseRequestId = response.headers.get(REQUEST_ID_HEADER) ?? requestId;

  if (response.status === 401 && path !== "/auth/refresh" && token) {
    const newToken = await refreshAccessToken(responseRequestId);
    if (newToken) {
      const retryHeaders = new Headers(headers);
      retryHeaders.set("Authorization", `Bearer ${newToken}`);
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: retryHeaders
      });
    }
  }

  if (!response.ok) {
    const { message, responseBody, detail } = await parseErrorResponse(response);
    const error = new ApiError(message, {
      status: response.status,
      path,
      method,
      requestId: responseRequestId,
      detail,
      responseBody
    });
    logError(error, {
      severity: response.status >= 500 ? "error" : "warn",
      title: "API 请求失败",
      context: {
        method,
        path,
        status: response.status,
        requestId: responseRequestId,
        responseBody
      }
    });
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function post<T>(path: string, body?: RequestBody) {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export function put<T>(path: string, body: RequestBody) {
  return request<T>(path, {
    method: "PUT",
    body: JSON.stringify(body)
  });
}

export function del<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

export function delWithBody<T>(path: string, body: RequestBody) {
  return request<T>(path, {
    method: "DELETE",
    body: JSON.stringify(body)
  });
}
