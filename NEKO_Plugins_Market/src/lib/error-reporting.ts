import { toast } from "sonner";

export type ErrorSeverity = "debug" | "info" | "warn" | "error" | "fatal";

export interface ErrorReportOptions {
  severity?: ErrorSeverity;
  title?: string;
  userMessage?: string;
  context?: Record<string, unknown>;
  toast?: boolean;
}

export interface NormalizedError {
  id: string;
  name: string;
  message: string;
  stack?: string;
  status?: number;
  method?: string;
  path?: string;
  requestId?: string;
  detail?: unknown;
}

export interface SuccessNotifyOptions {
  description?: string;
  context?: Record<string, unknown>;
}

let globalHandlersInstalled = false;

function createErrorId() {
  return `NEKO-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`.toUpperCase();
}

export function normalizeError(error: unknown): NormalizedError {
  const record = typeof error === "object" && error !== null ? error as Record<string, unknown> : {};
  const message = error instanceof Error
    ? error.message
    : typeof error === "string"
      ? error
      : "未知错误";

  return {
    id: createErrorId(),
    name: error instanceof Error ? error.name : "UnknownError",
    message,
    stack: error instanceof Error ? error.stack : undefined,
    status: typeof record.status === "number" ? record.status : undefined,
    method: typeof record.method === "string" ? record.method : undefined,
    path: typeof record.path === "string" ? record.path : undefined,
    requestId: typeof record.requestId === "string"
      ? record.requestId
      : typeof record.request_id === "string"
        ? record.request_id
        : undefined,
    detail: record.detail
  };
}

export function getErrorMessage(error: unknown, fallback = "操作失败，请稍后重试。") {
  const normalized = normalizeError(error);
  return normalized.message || fallback;
}

export function logError(error: unknown, options: ErrorReportOptions = {}) {
  const severity = options.severity ?? "error";
  const normalized = normalizeError(error);
  const title = options.title ?? "前端错误";
  const method = normalized.method ? `${normalized.method} ` : "";
  const path = normalized.path ?? "";
  const status = normalized.status ? ` [${normalized.status}]` : "";
  const requestId = normalized.requestId ? ` request_id=${normalized.requestId}` : "";
  const header = `[${severity.toUpperCase()}] ${title} ${method}${path}${status} #${normalized.id}${requestId}`;
  const payload = {
    error: normalized,
    context: options.context ?? {},
    timestamp: new Date().toISOString(),
    location: typeof window !== "undefined" ? window.location.href : undefined
  };

  const printer = severity === "fatal" || severity === "error"
    ? console.error
    : severity === "warn"
      ? console.warn
      : console.info;

  if (console.groupCollapsed) {
    console.groupCollapsed(header);
    printer(payload);
    if (normalized.stack) {
      console.debug(normalized.stack);
    }
    console.groupEnd();
  } else {
    printer(header, payload);
  }

  return normalized;
}

export function reportError(error: unknown, options: ErrorReportOptions = {}) {
  const normalized = logError(error, options);
  if (options.toast !== false) {
    const title = options.title ?? "操作失败";
    const description = options.userMessage ?? normalized.message;
    const requestIdText = normalized.requestId ? `；请求编号：${normalized.requestId}` : "";
    toast.error(title, {
      description: `${description}（错误编号：${normalized.id}${requestIdText}）`
    });
  }
  return normalized;
}

export function notifySuccess(message: string, options?: string | SuccessNotifyOptions) {
  const description = typeof options === "string" ? options : options?.description;
  const context = typeof options === "string" ? {} : options?.context ?? {};
  toast.success(message, { description });
  console.info(`[SUCCESS] ${message}`, {
    description,
    context,
    timestamp: new Date().toISOString(),
    location: typeof window !== "undefined" ? window.location.href : undefined
  });
}

export function installGlobalErrorHandlers() {
  if (globalHandlersInstalled || typeof window === "undefined") {
    return;
  }
  globalHandlersInstalled = true;

  window.addEventListener("error", (event) => {
    reportError(event.error ?? event.message, {
      severity: "fatal",
      title: "页面运行错误",
      userMessage: "页面运行时出现异常，请查看控制台错误编号。",
      context: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    reportError(event.reason, {
      severity: "fatal",
      title: "未处理的异步错误",
      userMessage: "后台请求或异步任务出现异常，请查看控制台错误编号。"
    });
  });
}
