"use client";

import { useEffect, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Trophy } from "lucide-react";
import type { ArcClaim } from "@/lib/zod";
import { haptics } from "@/lib/haptics";

const COLORS = ["#fbbf24", "#f59e0b", "#fde68a", "#ffffff", "#fcd34d", "#b45309"];

/**
 * Variable-ratio reward celebration. Escalates with rarity:
 *   common    → subtle toast handled by the caller (no overlay)
 *   rare      → gold particle burst
 *   epic      → screen shake + gold confetti
 *   legendary → full-screen confetti + exclusive badge banner
 */
export function RewardCelebration({
  claim,
  onDone,
}: {
  claim: ArcClaim | null;
  onDone: () => void;
}) {
  const reward = claim?.reward ?? null;
  const rarity = reward?.rarity ?? "common";
  const show = claim != null && rarity !== "common";

  useEffect(() => {
    if (!show) return;
    const t = setTimeout(onDone, 2800);
    return () => clearTimeout(t);
  }, [show, onDone]);

  // A variable-ratio win should land in the body, not only on the screen: one
  // short buzz at the moment the burst starts (Android only, gesture-gated —
  // `lib/haptics.ts`). No buzz for a "common" drop, which is why the caller
  // renders a toast instead of this overlay for those.
  useEffect(() => {
    if (show) haptics.celebrate();
  }, [show]);

  const count = rarity === "legendary" ? 60 : rarity === "epic" ? 40 : 18;
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 0.4,
        size: 6 + Math.random() * 10,
        color: COLORS[i % COLORS.length],
        rotate: (Math.random() - 0.5) * 720,
        duration: 2 + (i % 5) * 0.3,
      })),
    [count],
  );

  const intense = rarity === "epic" || rarity === "legendary";

  return (
    <AnimatePresence>
      {show ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-black/70" onClick={onDone} aria-hidden />

          <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
            {particles.map((p) => (
              <motion.span
                key={p.id}
                className="absolute top-0 rounded-sm"
                style={{
                  left: `${p.left}%`,
                  width: p.size,
                  height: p.size,
                  backgroundColor: p.color,
                }}
                initial={{ y: -24, opacity: 1, rotate: 0 }}
                animate={{ y: "110vh", opacity: [1, 1, 0], rotate: p.rotate }}
                transition={{ duration: p.duration, delay: p.delay, ease: "easeIn" }}
              />
            ))}
          </div>

          <motion.div
            className="relative flex flex-col items-center px-10 py-8 text-center"
            initial={{ scale: 0.8, y: 20 }}
            animate={
              intense
                ? { scale: [0.8, 1.06, 1], y: 0, x: [0, -6, 6, -4, 4, 0] }
                : { scale: 1, y: 0 }
            }
            transition={{ duration: 0.5 }}
          >
            {rarity === "legendary" ? (
              <Trophy className="mb-1 h-12 w-12 text-gold-bright" aria-hidden />
            ) : null}
            <p className="font-display text-5xl font-black text-gold-bright">
              +{claim?.xp_awarded}
            </p>
            <p className="mt-1 text-xl font-semibold text-white">
              {reward?.label || "XP"}
            </p>
            {reward?.badge ? (
              <p className="mt-3 inline-flex items-center gap-1 rounded-full bg-gold/20 px-4 py-1.5 text-sm font-semibold text-gold-bright">
                🏆 Legendary badge unlocked
              </p>
            ) : null}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
