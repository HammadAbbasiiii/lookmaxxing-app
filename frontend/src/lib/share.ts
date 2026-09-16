import { toast } from "sonner";

/**
 * Share text via the native sheet when available, falling back to the
 * clipboard. Never throws — a user dismissing the share sheet is a no-op.
 *
 * Extracted from InsightSections so the results reveal can offer the same
 * behaviour without duplicating the fallback logic.
 */
export async function shareText(
  text: string,
  opts?: { title?: string; copied?: string },
): Promise<void> {
  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share({ title: opts?.title ?? "LookMaxx", text });
      return;
    } catch (err) {
      // User dismissed the sheet (AbortError) — treat as a no-op, not a failure.
      if (err instanceof DOMException && err.name === "AbortError") return;
    }
  }
  try {
    await navigator.clipboard.writeText(text);
    toast.success(opts?.copied ?? "Copied to clipboard");
  } catch {
    toast.error("Couldn't share — copy it manually");
  }
}
