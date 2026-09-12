"use client";

import { useState, type ReactNode } from "react";
import { ImageIcon } from "lucide-react";
import { cn, safeUrl } from "@/lib/utils";

interface SafeImageProps {
  src: string | null | undefined;
  alt: string;
  className?: string;
  /** Custom placeholder shown when the image is missing or fails to load. */
  fallback?: ReactNode;
}

/**
 * Defensive image rendering (§9.5): validates http(s), appends Cloudinary
 * auto-format, and falls back to a placeholder on any load error — never a
 * broken layout.
 */
export function SafeImage({ src, alt, className, fallback }: SafeImageProps) {
  const [failed, setFailed] = useState(false);
  const url = safeUrl(src);

  if (!url || failed) {
    return (
      <div
        className={cn("flex items-center justify-center bg-surface-2 text-muted", className)}
        aria-label={alt}
        role="img"
      >
        {fallback ?? <ImageIcon className="h-6 w-6" aria-hidden />}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={alt}
      className={cn("object-cover", className)}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
