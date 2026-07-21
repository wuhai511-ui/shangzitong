import type { Page } from "@playwright/test";

function cashflowDay(offset = 0): Record<string, unknown> {
  const base = new Date("2026-07-21");
  base.setDate(base.getDate() + offset);
  const iso = base.toISOString().slice(0, 10);
  return {
    date: iso,
    opening_balance: "10000.00",
    settlements: "0.00",
    repayments: "0.00",
    purchases: "0.00",
    other_outflows: "0.00",
    closing_balance: "10000.00",
    funding_gap: "0.00",
    events: [],
  };
}

function scheduleDay(): Record<string, unknown> {
  return {
    date: "2026-07-21",
    cash_pool: "10000.00",
    funding_gap: "0.00",
    settlements: [{ amount: "0.00" }],
    repayments: [],
    alerts: [],
  };
}

/** Fulfill /api/v1/** with deterministic fixtures and assert mutation bodies. */
export async function mockBackend(page: Page): Promise<void> {
  let cash: string | null = null;

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === "/api/v1/profile/cash" && method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available_cash: cash,
          available_cash_updated_at: null,
          is_estimate: cash === null,
        }),
      });
    }

    if (path === "/api/v1/profile/cash" && method === "PUT") {
      const body = request.postDataJSON();
      cash = body?.available_cash ?? null;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available_cash: cash,
          available_cash_updated_at: "2026-07-21T00:00:00Z",
          is_estimate: false,
        }),
      });
    }

    if (path.startsWith("/api/v1/cashflow")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          days: Array.from({ length: 30 }, (_, i) => cashflowDay(i)),
          is_estimate: cash === null,
          available_cash: cash,
          available_cash_updated_at: null,
        }),
      });
    }

    if (path === "/api/v1/cards") {
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }

    if (path === "/api/v1/schedule") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ days: [scheduleDay()] }),
      });
    }

    if (path === "/api/v1/recommend") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recommendations: [],
          multi_card_split: [],
          coverage_ratio: 1,
          gap_amount: "0.00",
          warnings: [],
        }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  });
}
