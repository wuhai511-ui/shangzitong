import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiClient, ApiErrorImpl } from "./client";

function okJson(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function errorJson(
  status: number,
  code: string,
  detail: string,
  requestId: string,
): Response {
  return new Response(JSON.stringify({ code, detail, request_id: requestId }), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
  });
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "";
});

describe("apiClient", () => {
  it("sends cookies and csrf token on mutations", async () => {
    document.cookie = "szt_csrf=csrf-123";
    fetchMock.mockResolvedValue(okJson({ saved: true }));
    await apiClient("/api/v1/profile/cash", {
      method: "PUT",
      body: JSON.stringify({ available_cash: "10.00" }),
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/profile/cash",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({ "X-CSRF-Token": "csrf-123" }),
      }),
    );
  });

  it("throws an ApiError with the server request id", async () => {
    fetchMock.mockResolvedValue(errorJson(422, "INVALID_AMOUNT", "金额格式错误", "req-7"));
    await expect(apiClient("/api/v1/profile/cash")).rejects.toMatchObject({
      code: "INVALID_AMOUNT",
      requestId: "req-7",
    });
  });

  it("does not set content-type for FormData bodies", async () => {
    const form = new FormData();
    const csv = "a,b" + String.fromCharCode(10) + "1,2";
    form.append("file", new Blob([csv]), "test.csv");
    fetchMock.mockResolvedValue(okJson({ ok: true }));
    await apiClient("/api/v1/upload", { method: "POST", body: form });
    const call = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = call[1].headers as Record<string, string>;
    expect(headers["Content-Type"]).toBeUndefined();
    expect(headers["Accept"]).toBe("application/json");
  });

  it("is a recognized ApiError instance", async () => {
    fetchMock.mockResolvedValue(errorJson(422, "BAD", "坏", "r-1"));
    await expect(apiClient("/x")).rejects.toBeInstanceOf(ApiErrorImpl);
  });
});
