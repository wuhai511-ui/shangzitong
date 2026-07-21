import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";

function renderShell(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell />
    </MemoryRouter>,
  );
}

it("shows the five approved primary destinations", () => {
  renderShell("/");
  for (const label of ["首页", "资金", "规划", "提醒", "我的"]) {
    expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
  }
});

it("marks the current destination", () => {
  renderShell("/planning");
  expect(screen.getByRole("link", { name: "规划" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});
