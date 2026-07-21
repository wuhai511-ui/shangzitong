import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { PlanningPage } from "./PlanningPage";

let mockHandler: (path: string, init?: RequestInit) => unknown = () => ({});

vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) =>
    mockHandler(path, init),
  ),
}));

function scheduleDay(gap: string) {
  return {
    date: "2026-07-21",
    cash_pool: "10000.00",
    funding_gap: gap,
    settlements: [{ amount: "0.00" }],
    repayments: [],
    alerts: [],
  };
}

function renderPlanning() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <PlanningPage />
    </QueryClientProvider>,
  );
}

function mockRecommendations(
  recs: Array<{ card_id: number; bank_name: string; score: number }>,
) {
  mockHandler = (path: string) => {
    if (path === "/api/v1/recommend")
      return {
        recommendations: recs,
        multi_card_split: [],
        coverage_ratio: 1,
        gap_amount: "0.00",
        warnings: [],
      };
    if (path === "/api/v1/schedule") return { days: [scheduleDay("0.00")] };
    if (path === "/api/v1/cards") return [];
    return {};
  };
}

function mockCashflowWithGap(gap: string) {
  const card = {
    id: 1,
    user_id: 1,
    bank_name: "测试银行",
    card_tail: "1234",
    credit_limit: "50000.00",
    temp_limit: "0.00",
    used_limit: "0.00",
    overpayment: "0.00",
    avail_limit: "50000.00",
    bill_day: 5,
    due_day: 25,
    swipe_fee_rate: "0.006",
    interest_rate: "0.0005",
    min_payment_ratio: "0.10",
    installment_amount: "0.00",
    bill_day_inclusive: 0,
    status: 1,
  };
  mockHandler = (path: string) => {
    if (path === "/api/v1/recommend")
      return {
        recommendations: [],
        multi_card_split: [],
        coverage_ratio: 0,
        gap_amount: gap,
        warnings: [],
      };
    if (path === "/api/v1/schedule") return { days: [scheduleDay(gap)] };
    if (path === "/api/v1/cards") return [card];
    if (path === "/api/v1/stoploss")
      return {
        plan_a: { name: "全额还款(临时借款)", description: "", cost: "10.00", total: "12810.00" },
        plan_b: { name: "最低还款", description: "", cost: "20.00", total: "12820.00" },
        plan_c: { name: "账单分期(6期)", description: "", cost: "30.00", total: "12830.00" },
        recommendation: "plan_a",
        recommendation_reason: "方案A总成本最低",
      };
    return {};
  };
}

it("shows recommended cards in ranked order", async () => {
  mockRecommendations([
    { card_id: 2, bank_name: "建设银行", score: 92 },
    { card_id: 1, bank_name: "招商银行", score: 81 },
  ]);
  renderPlanning();
  const cards = await screen.findAllByTestId("recommendation-card");
  expect(cards[0]).toHaveTextContent("建设银行");
});

it("shows stop-loss options only when a gap exists", async () => {
  mockCashflowWithGap("12800.00");
  renderPlanning();
  expect(await screen.findByText("全额借款")).toBeInTheDocument();
  expect(screen.getByText("最低还款")).toBeInTheDocument();
  expect(screen.getByText("分期")).toBeInTheDocument();
});
