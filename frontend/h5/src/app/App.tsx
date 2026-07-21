import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./AppShell";
import { routes } from "./routes";

let router: ReturnType<typeof createBrowserRouter> | null = null;

function getRouter() {
  if (!router) {
    router = createBrowserRouter(
      [
        {
          path: "/",
          element: <AppShell />,
          children: routes,
        },
      ],
      { basename: "/szt/" },
    );
  }
  return router;
}

export function App() {
  return <RouterProvider router={getRouter()} />;
}
