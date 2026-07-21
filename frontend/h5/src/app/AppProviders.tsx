import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: (failureCount, error) => {
              // No retry for 4xx client errors; one retry for network failures.
              const status = (error as { status?: number }).status;
              if (status !== undefined && status >= 400 && status < 500) {
                return false;
              }
              return failureCount < 1;
            },
            refetchOnWindowFocus: false,
            staleTime: 30_000,
          },
          mutations: {
            retry: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
