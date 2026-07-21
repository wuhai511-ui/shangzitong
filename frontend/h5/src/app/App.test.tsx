import { render, screen } from "@testing-library/react";
import { App } from "./App";
import { AppProviders } from "./AppProviders";

it("renders the application title", () => {
  window.history.replaceState({}, "", "/szt/");
  render(
    <AppProviders>
      <App />
    </AppProviders>,
  );
  expect(screen.getByRole("heading", { name: "商资通" })).toBeInTheDocument();
});
