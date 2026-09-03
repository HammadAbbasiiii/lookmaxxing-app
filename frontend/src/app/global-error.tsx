"use client";

import { Button } from "@/components/ui/Button";

/** Root error boundary — catches errors even in the root layout. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ background: "#0a0a0a", color: "#f5f5f5", fontFamily: "system-ui, sans-serif" }}>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            padding: 24,
          }}
        >
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>Something went wrong</h1>
          <p style={{ color: "#9ca3af", maxWidth: 360 }}>
            {error?.message || "An unexpected error occurred."}
          </p>
          <Button onClick={reset}>Reload</Button>
        </div>
      </body>
    </html>
  );
}
