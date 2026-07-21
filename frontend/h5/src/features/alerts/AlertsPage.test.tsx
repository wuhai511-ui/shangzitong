import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { AlertsPage } from "./AlertsPage";

let mockHandler: (path: string, init?: RequestInit) => unknown = () => ({});

vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) =>
    mockHandler(path, init),
  ),
}));

function mockUpcoming(
  repayments: Array<{ due_date: string; funding_gap: string }>,
) {
  mockHandler = (path: string) => {
    if (path === "/api/v1/alerts/upcoming") return { repayments };
    if (path === "/api/v1/alerts/daily-summary")
      return {
        date: "2026-07-21",
        total_due: "0.00",
        forecasted_settlements: "0.00",
        gap: "0.00",
        repayments: [],
      };
    return {};
  };
}

function renderAlerts() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AlertsPage />
    </QueryClientProvider>,
  );
}

it("uses the canonical funding gap in an alert", async () => {
  mockUpcoming([{ due_date: "2026-07-26", funding_gap: "12800.00" }]);
  renderAlerts();
  expect(await screen.findByText("¥12,800.00")).toBeInTheDocument();
});
