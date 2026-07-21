import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./AppShell";
import { routes } from "./routes";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: routes,
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
