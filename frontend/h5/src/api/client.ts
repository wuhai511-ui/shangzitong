import type { ApiError, User } from "./types";

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCsrfCookie(): string | undefined {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("szt_csrf="));
  return match?.split("=")[1];
}

export class ApiErrorImpl extends Error implements ApiError {
  code: string;
  requestId: string;
  status: number;

  constructor(
    message: string,
    code: string,
    requestId: string,
    status: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.requestId = requestId;
    this.status = status;
  }
}

interface FetchLike {
  (input: string, init?: RequestInit): Promise<Response>;
}

type HeaderRecord = Record<string, string>;

function buildHeaders(
  init: RequestInit,
  isFormData: boolean,
  isUnsafe: boolean,
): HeaderRecord {
  const base: HeaderRecord = { Accept: "application/json" };
  const incoming = init.headers;
  if (incoming) {
    if (incoming instanceof Headers) {
      incoming.forEach((value, key) => {
        base[key] = value;
      });
    } else if (Array.isArray(incoming)) {
      for (const [key, value] of incoming) {
        base[key] = value;
      }
    } else {
      Object.assign(base, incoming);
    }
  }
  if (init.body && !isFormData && !base["Content-Type"]) {
    base["Content-Type"] = "application/json";
  }
  if (isUnsafe) {
    const csrf = readCsrfCookie();
    if (csrf) {
      base["X-CSRF-Token"] = csrf;
    }
  }
  return base;
}

export async function apiClient<T>(
  path: string,
  init: RequestInit = {},
  fetchImpl: FetchLike = fetch,
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const isUnsafe = UNSAFE_METHODS.has(method);
  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;

  const headers = buildHeaders(init, isFormData, isUnsafe);

  const response = await fetchImpl(path, {
    ...init,
    method,
    credentials: "include",
    headers,
  });

  if (response.status === 401) {
    // Attempt a single session bootstrap + retry.
    await fetchImpl("/api/v1/auth/session", {
      method: "POST",
      credentials: "include",
    });
    const retry = await fetchImpl(path, {
      ...init,
      method,
      credentials: "include",
      headers,
    });
    if (retry.status === 401) {
      throw new ApiErrorImpl("未登录", "UNAUTHORIZED", "", 401);
    }
    return parseResponse<T>(retry);
  }

  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let code = "REQUEST_FAILED";
    let message = "请求失败";
    let requestId = response.headers.get("X-Request-Id") ?? "";
    try {
      const body = await response.json();
      if (body?.code) code = body.code;
      if (body?.detail) message = body.detail;
      if (body?.request_id) requestId = body.request_id;
    } catch {
      // Non-JSON error body; keep defaults.
    }
    throw new ApiErrorImpl(message, code, requestId, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function bootstrapSession(
  fetchImpl: FetchLike = fetch,
): Promise<User> {
  return apiClient<User>(
    "/api/v1/auth/session",
    { method: "POST" },
    fetchImpl,
  );
}
