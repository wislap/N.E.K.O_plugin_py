export class ApiError extends Error {
  status: number;
  path: string;
  method: string;
  requestId: string;
  detail?: unknown;
  responseBody?: unknown;

  constructor(message: string, options: {
    status: number;
    path: string;
    method: string;
    requestId: string;
    detail?: unknown;
    responseBody?: unknown;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.path = options.path;
    this.method = options.method;
    this.requestId = options.requestId;
    this.detail = options.detail;
    this.responseBody = options.responseBody;
  }
}

export async function parseErrorResponse(response: Response) {
  let message = `请求失败：${response.status}`;
  let responseBody: unknown;
  let detail: unknown;

  try {
    const data = await response.clone().json() as { detail?: unknown };
    responseBody = data;
    detail = data.detail;
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail
        .map((item) => {
          if (typeof item === "object" && item && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join("；");
    }
  } catch {
    const text = await response.text();
    responseBody = text;
    message = text || message;
  }

  return { message, responseBody, detail };
}
