import { render, screen } from "@testing-library/react";
import { App } from "./App";

it("renders the application title", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "商资通" })).toBeInTheDocument();
});
