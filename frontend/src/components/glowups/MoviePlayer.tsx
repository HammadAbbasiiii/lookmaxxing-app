"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Pause, Play, Share2 } from "lucide-react";
import { toast } from "sonner";
import { SafeImage } from "@/components/ui/SafeImage";
import { Button } from "@/components/ui/Button";
import { formatScore } from "@/lib/utils";

const FRAME_MS = 1800; // ~0.5s crossfade + hold on each frame

/**
 * Client-side "transformation movie" — a Ken Burns slideshow built from the
 * member's own ordered photos. Fades between frames, draws the score progression
 * as a sparkline, and offers Share (Web Share API) / frame download. No server
 * video encoding required; the server only supplies the ordered photo URLs.
 */
export function MoviePlayer({
  photoUrls,
  photoScores,
  delta,
  status,
}: {
  photoUrls: string[];
  photoScores: number[];
  delta: number;
  status: string;
}) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);

  const frames = useMemo(() => photoUrls.filter(Boolean), [photoUrls]);
  const count = frames.length;

  useEffect(() => {
    if (!playing || count < 2) return;
    const id = setInterval(() => setIndex((i) => (i + 1) % count), FRAME_MS);
    return () => clearInterval(id);
  }, [playing, count]);

  if (count === 0) {
    return (
      <p className="mt-3 text-sm text-muted">
        Upload at least two scored photos to compile your movie.
      </p>
    );
  }

  const progress = ((index + 1) / count) * 100;
  const scores =
    photoScores.length >= count ? photoScores.slice(0, count) : photoScores;

  async function share() {
    const text = `My LookMaxx glow-up movie: +${formatScore(delta)} pts across ${count} check-ins.`;
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ title: "My LookMaxx Glow-Up", text });
      } else if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        toast.success("Copied share text to clipboard");
      }
    } catch {
      /* user cancelled the share sheet — nothing to do */
    }
  }

  function downloadFrame() {
    const url = frames[index];
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="mt-3">
      <div className="relative aspect-[4/5] overflow-hidden rounded-xl bg-black">
        <AnimatePresence initial={false}>
          <motion.div
            key={index}
            initial={{ opacity: 0, scale: 1.05 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="absolute inset-0"
          >
            <SafeImage
              src={frames[index]}
              alt={`Progress frame ${index + 1} of ${count}`}
              className="h-full w-full"
            />
          </motion.div>
        </AnimatePresence>

        {/* Score progression overlay */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/85 to-transparent p-3">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-white/70">
                {status === "ready" ? "Your transformation" : "Progress preview"} · {index + 1}/{count}
              </p>
              {delta > 0 ? (
                <p className="text-sm font-bold text-gold-bright">
                  +{formatScore(delta)} pts since Day 1
                </p>
              ) : null}
            </div>
            {scores.length > 0 ? <ScoreSparkline scores={scores} active={index} /> : null}
          </div>
        </div>
      </div>

      {/* Frame progress bar */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <motion.div
          className="h-full gold-gradient"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button size="sm" variant="secondary" onClick={() => setPlaying((p) => !p)}>
          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          {playing ? "Pause" : "Play"}
        </Button>
        <Button size="sm" variant="secondary" onClick={share}>
          <Share2 className="h-3.5 w-3.5" /> Share
        </Button>
        <Button size="sm" variant="secondary" onClick={downloadFrame}>
          <Download className="h-3.5 w-3.5" /> Frame
        </Button>
      </div>
    </div>
  );
}

function ScoreSparkline({ scores, active }: { scores: number[]; active: number }) {
  if (scores.length < 2) return null;
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1;
  const w = 96;
  const h = 32;
  const step = w / (scores.length - 1);
  const points = scores.map((s, i) => {
    const x = i * step;
    const y = h - ((s - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="shrink-0" aria-hidden>
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="rgba(212,175,55,0.9)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {points.map((p, i) => {
        const [x, y] = p.split(",").map(Number);
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r={i === active ? 3 : 1.6}
            fill={i === active ? "#fff" : "rgba(212,175,55,0.9)"}
          />
        );
      })}
    </svg>
  );
}
