import { render, screen } from "@testing-library/react";
import { ErrorState, EmptyState, LoadingState } from "./AsyncState";

it("shows a loading indicator", () => {
  render(<LoadingState />);
  expect(screen.getByText("加载中")).toBeInTheDocument();
  expect(screen.getByRole("status")).toBeInTheDocument();
});

it("shows empty copy", () => {
  render(<EmptyState label="暂无信用卡" />);
  expect(screen.getByText("暂无信用卡")).toBeInTheDocument();
});

it("shows a retry button on error", () => {
  const onRetry = vi.fn();
  render(<ErrorState onRetry={onRetry} />);
  expect(screen.getByText("加载失败，请重试")).toBeInTheDocument();
  const button = screen.getByRole("button", { name: "重试" });
  button.click();
  expect(onRetry).toHaveBeenCalledOnce();
});
