// Privacy-first, self-hosted event tracking (PRODUCT_SPEC §17).
// Fire-and-forget, batched, and guaranteed to never throw into the UI.
// Events carry no faces, no emails, no tokens in their payloads.

import { API_BASE } from "@/lib/constants";
import { getToken } from "@/lib/auth";

export interface TrackEvent {
  event_name: string;
  page?: string;
  referrer?: string | null;
  session_id?: string;
  metadata?: Record<string, unknown>;
}

let sessionId = "";
let queue: TrackEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;
const BATCH_SIZE = 20;
const FLUSH_MS = 1500;

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  if (sessionId) return sessionId;
  try {
    sessionId = sessionStorage.getItem("lmx_sid") ?? "";
    if (!sessionId) {
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      sessionId = id;
      sessionStorage.setItem("lmx_sid", id);
    }
  } catch {
    sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }
  return sessionId;
}

export function track(
  event_name: string,
  data: { page?: string; referrer?: string | null; metadata?: Record<string, unknown> } = {},
): void {
  if (typeof window === "undefined") return;
  queue.push({
    event_name,
    session_id: getSessionId(),
    page: data.page ?? window.location.pathname,
    referrer: data.referrer ?? (document.referrer || null),
    metadata: data.metadata,
  });
  if (queue.length >= BATCH_SIZE) void flush();
  else if (!flushTimer) flushTimer = setTimeout(() => void flush(), FLUSH_MS);
}

async function flush(): Promise<void> {
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  if (!queue.length) return;
  const events = queue;
  queue = [];
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    await fetch(`${API_BASE}/track`, {
      method: "POST",
      headers,
      body: JSON.stringify({ events }),
      keepalive: true,
    });
  } catch {
    // analytics must never break the app
  }
}

// Flush on page hide / tab switch so time-spent metrics are not lost.
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", () => void flush());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void flush();
  });
}
