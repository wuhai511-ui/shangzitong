import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { ManualSettlementPanel } from "./ManualSettlementPanel";

const api = { create: vi.fn(), del: vi.fn() };
let listResponse: unknown[] = [];

beforeEach(() => {
  api.create.mockClear();
  api.del.mockClear();
  listResponse = [];
});
vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/api/v1/manual-settlement" && init?.method === "POST") {
      const body = JSON.parse((init.body as string) ?? "{}");
      api.create(body);
      listResponse = [
        { id: 1, period_type: body.period_type, period_date: body.period_date, amount: body.amount, note: body.note ?? null, created_at: "2026-07-21T00:00:00Z" },
      ];
      return (listResponse as unknown[])[0];
    }
    if (path.startsWith("/api/v1/manual-settlement/") && init?.method === "DELETE") {
      const id = Number(path.split("/").pop());
      api.del(id);
      listResponse = [];
      return undefined;
    }
    if (path === "/api/v1/manual-settlement") {
      return listResponse;
    }
    return {};
  }),
}));

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  vi.spyOn(queryClient, "invalidateQueries");
  render(
    <QueryClientProvider client={queryClient}>
      <ManualSettlementPanel />
    </QueryClientProvider>,
  );
  return queryClient;
}

it("renders the form with day/month selector, date, amount, note, submit", () => {
  renderPanel();
  expect(screen.getByText("手动结算录入")).toBeInTheDocument();
  expect(screen.getByLabelText("结算日期")).toBeInTheDocument();
  expect(screen.getByLabelText("结算金额")).toBeInTheDocument();
  expect(screen.getByLabelText("备注")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "保存" })).toBeInTheDocument();
});

it("submits a valid day entry with correct body", async () => {
  const user = userEvent.setup();
  renderPanel();
  await user.type(screen.getByLabelText("结算日期"), "2026-07-15");
  await user.type(screen.getByLabelText("结算金额"), "1000");
  await user.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() =>
    expect(api.create).toHaveBeenCalledWith({
      period_type: "day",
      period_date: "2026-07-15",
      amount: "1000.00",
      note: undefined,
    }),
  );
});

it("switching to month mode sends period_date as first-of-month", async () => {
  const user = userEvent.setup();
  renderPanel();
  await user.click(screen.getByLabelText("按月"));
  await user.type(screen.getByLabelText("结算月份"), "2026-06");
  await user.type(screen.getByLabelText("结算金额"), "300000");
  await user.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() =>
    expect(api.create).toHaveBeenCalledWith({
      period_type: "month",
      period_date: "2026-06-01",
      amount: "300000.00",
      note: undefined,
    }),
  );
});

it("renders existing entries from the query with a delete button", async () => {
  listResponse = [
    { id: 7, period_type: "day", period_date: "2026-07-10", amount: "500.00", note: "test", created_at: "2026-07-21T00:00:00Z" },
  ];
  renderPanel();
  expect(await screen.findByText("¥500.00")).toBeInTheDocument();
  expect(screen.getByText("test")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "删除 2026-07-10" })).toBeInTheDocument();
});

it("shows an empty state when no entries", async () => {
  listResponse = [];
  renderPanel();
  expect(await screen.findByText("暂无手动结算记录")).toBeInTheDocument();
});

it("blocks submit with invalid amount", async () => {
  const user = userEvent.setup();
  renderPanel();
  await user.type(screen.getByLabelText("结算日期"), "2026-07-15");
  await user.type(screen.getByLabelText("结算金额"), "-5");
  await user.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() => expect(screen.getByText("金额不能为空且最多两位小数")).toBeInTheDocument());
  expect(api.create).not.toHaveBeenCalled();
});
