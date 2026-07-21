import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { AvailableCashForm } from "./AvailableCashForm";

const api = { putCash: vi.fn() };

vi.mock("../../api/client", () => ({
  apiClient: vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/api/v1/profile/cash" && init?.method === "PUT") {
      const body = JSON.parse((init.body as string) ?? "{}");
      api.putCash(body.available_cash);
      return {
        available_cash: body.available_cash,
        available_cash_updated_at: null,
        is_estimate: false,
      };
    }
    return {};
  }),
}));

function renderAvailableCashForm() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  vi.spyOn(queryClient, "invalidateQueries");
  render(
    <QueryClientProvider client={queryClient}>
      <AvailableCashForm />
    </QueryClientProvider>,
  );
  return queryClient;
}

it("allows zero and invalidates cashflow after saving", async () => {
  const user = userEvent.setup();
  const queryClient = renderAvailableCashForm();
  await user.type(screen.getByLabelText("当前可用资金"), "0");
  await user.click(screen.getByRole("button", { name: "保存并重新计算" }));
  await waitFor(() => expect(api.putCash).toHaveBeenCalledWith("0.00"));
  expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
    queryKey: ["cashflow"],
  });
});
