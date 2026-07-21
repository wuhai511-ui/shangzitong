import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { FundsPage } from "./FundsPage";

const api = { confirmUpload: vi.fn() };

vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/api/v1/ingest/upload/preview") {
      return {
        preview_id: "preview-1",
        mappings: { date_column: "date", amount_column: "amount" },
        preview_rows: [
          { date: "2026-07-20", amount: "100.00" },
          { date: "2026-07-21", amount: "200.00" },
        ],
        total_rows: 2,
        expires_at: "2026-07-21T12:00:00Z",
      };
    }
    if (path === "/api/v1/ingest/upload/confirm") {
      const body = JSON.parse((init?.body as string) ?? "{}");
      api.confirmUpload(body);
      return { imported: 2 };
    }
    if (path === "/api/v1/cards") return [];
    if (path === "/api/v1/profile/cash")
      return { available_cash: null, available_cash_updated_at: null, is_estimate: true };
    return {};
  }),
}));

function renderFundsPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <FundsPage />
    </QueryClientProvider>,
  );
}

it("renders disabled email and SFTP cards", async () => {
  renderFundsPage();
  expect(await screen.findByText("邮件接入")).toHaveAttribute("aria-disabled", "true");
  expect(screen.getByText("SFTP 接入")).toHaveAttribute("aria-disabled", "true");
  expect(screen.getAllByText("正在开发中")).toHaveLength(2);
});

it("previews and confirms an upload with preview_id", async () => {
  const user = userEvent.setup();
  renderFundsPage();
  const csv = "date,amount" + String.fromCharCode(10) + "2026-07-20,100.00" + String.fromCharCode(10) + "2026-07-21,200.00";
  const csvFile = new File([csv], "settlements.csv", { type: "text/csv" });
  await user.upload(screen.getByLabelText("选择结算文件"), csvFile);
  expect(await screen.findByText("共 2 行")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "确认导入" }));
  await waitFor(() =>
    expect(api.confirmUpload).toHaveBeenCalledWith(
      expect.objectContaining({ preview_id: "preview-1" }),
    ),
  );
});
