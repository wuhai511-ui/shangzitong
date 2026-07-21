import { expect, test } from "@playwright/test";
import { mockBackend } from "./fixtures";

test("merchant completes the core H5 flow", async ({ page }) => {
  await mockBackend(page);
  await page.goto("/szt/");
  await expect(page.getByRole("heading", { name: "资金指挥舱" })).toBeVisible();

  await page.getByRole("link", { name: "资金" }).click();
  await page.getByLabel("当前可用资金").fill("50000");
  await page.getByRole("button", { name: "保存并重新计算" }).click();
  await expect(page.getByText("¥50,000.00")).toBeVisible();

  await page.getByRole("link", { name: "规划" }).click();
  await expect(page.getByText("进货推荐")).toBeVisible();
});
