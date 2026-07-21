import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { ReportPage } from "./ReportPage";

let mockHandler: (path: string, init?: RequestInit) => unknown = () => ({});

vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) =>
    mockHandler(path, init),
  ),
}));

function mockReport(overrides: Record<string, unknown> = {}) {
  mockHandler = (path: string) => {
    if (path === "/api/v1/report/monthly")
      return {
        score: 75,
        grade: "良好",
        dimensions: { "免息期利用率": 80, "资金稳定性": 70, "额度健康度": 60 },
        card_count: 2,
        total_limit: "100000.00",
        avg_utilization: 40,
        suggestions: [],
        repayment_data_status: "unavailable",
        ...overrides,
      };
    return {};
  };
}

function renderReport() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ReportPage />
    </QueryClientProvider>,
  );
}

it("does not claim repayment punctuality without source data", async () => {
  mockReport({ repayment_data_status: "unavailable" });
  renderReport();
  expect(await screen.findByText("暂无真实还款记录")).toBeInTheDocument();
  expect(screen.queryByText("还款准时率100%")).not.toBeInTheDocument();
});
