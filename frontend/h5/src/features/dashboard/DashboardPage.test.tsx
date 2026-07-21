import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import type { CashflowDay, CashflowResponse } from "../../api/types";

function makeDays(n: number): CashflowDay[] {
  const base = new Date("2026-07-21");
  const days: CashflowDay[] = [];
  for (let i = 0; i < n; i++) {
    const d = new Date(base);
    d.setDate(base.getDate() + i);
    days.push({
      date: d.toISOString().slice(0, 10),
      opening_balance: "10000.00",
      settlements: "0.00",
      repayments: "0.00",
      purchases: "0.00",
      other_outflows: "0.00",
      closing_balance: "10000.00",
      funding_gap: "0.00",
      events: [],
    });
  }
  return days;
}

async function renderDashboard(opts: {
  available_cash: string | null;
  is_estimate: boolean;
}) {
  const response: CashflowResponse = {
    days: makeDays(30),
    is_estimate: opts.is_estimate,
    available_cash: opts.available_cash,
    available_cash_updated_at: null,
  };
  vi.doMock("../../api/client", () => ({
    apiClient: vi.fn(async (path: string) => {
      if (path.startsWith("/api/v1/cashflow")) return response;
      if (path === "/api/v1/cards") return [];
      if (path === "/api/v1/profile/cash")
        return {
          available_cash: opts.available_cash,
          available_cash_updated_at: null,
          is_estimate: opts.is_estimate,
        };
      return {};
    }),
  }));
  vi.resetModules();
  const { DashboardPage } = await import("./DashboardPage");
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

it("labels the dashboard as an estimate when cash is unset", async () => {
  await renderDashboard({ available_cash: null, is_estimate: true });
  expect(await screen.findByText("试算")).toBeInTheDocument();
  expect(screen.getByText("起始资金未设置")).toBeInTheDocument();
});
