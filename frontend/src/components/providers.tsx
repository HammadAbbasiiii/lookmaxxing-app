"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { Toaster } from "sonner";

export function Providers({ children }: { children: ReactNode }) {
  // One QueryClient for the whole session; refetch-on-mount + 2 retries by
  // default keep the app resilient without hammering the API.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 2,
            refetchOnMount: true,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {/* Respect the OS "reduce motion" preference for every framer-motion
          animation (§13 accessibility) — no vestibular-triggering motion. */}
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
      <Toaster
        position="top-center"
        theme="dark"
        toastOptions={{
          style: {
            background: "#1a1a1a",
            color: "#f5f5f5",
            border: "1px solid #262626",
          },
        }}
      />
    </QueryClientProvider>
  );
}
