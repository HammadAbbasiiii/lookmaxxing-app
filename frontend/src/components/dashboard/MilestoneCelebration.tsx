"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Share2, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { haptics } from "@/lib/haptics";

const META: Record<number, { emoji: string; title: string; badge: string }> = {
  7: { emoji: "🌱", title: "One Week Strong", badge: "Week One" },
  30: { emoji: "⚡", title: "Phase 1 Complete", badge: "Unstoppable" },
  60: { emoji: "🛡️", title: "Mid-Point", badge: "Unshakeable" },
  90: { emoji: "🏆", title: "Transformation Complete", badge: "Transformed" },
};

const COLORS = ["#fbbf24", "#f59e0b", "#fde68a", "#ffffff", "#fcd34d", "#34d399", "#60a5fa", "#f472b6"];

/**
 * Full-screen milestone takeover (Day 7/30/60/90). Shows confetti, an animated
 * badge unlock, and a share action. Persists a dismiss flag in localStorage so
 * each milestone only celebrates once.
 */
export function MilestoneCelebration({ day }: { day: number }) {
  const meta = META[day];
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!meta) return;
    const key = `milestone_celebration_${day}`;
    if (typeof window !== "undefined" && !window.localStorage.getItem(key)) {
      setVisible(true);
      // Day 7/30/60/90 is the one genuinely rare moment in the product, so it
      // gets the reserved multi-pulse pattern — never the everyday tick.
      haptics.celebrate();
    }
  }, [day, meta]);

  const particles = useMemo(
    () =>
      Array.from({ length: 80 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 0.5,
        size: 6 + Math.random() * 10,
        color: COLORS[i % COLORS.length],
        rotate: (Math.random() - 0.5) * 720,
        duration: 2.5 + (i % 6) * 0.3,
      })),
    [],
  );

  if (!meta) return null;

  function close() {
    setVisible(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(`milestone_celebration_${day}`, "1");
    }
  }

  async function share() {
    const text = `Day ${day}/90 on LookMaxx — ${meta.title} 🎉`;
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ title: "LookMaxx milestone", text });
      } else if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        toast.success("Copied share text to clipboard");
      }
    } catch {
      /* cancelled */
    }
  }

  return (
    <AnimatePresence>
      {visible ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
            {particles.map((p) => (
              <motion.span
                key={p.id}
                className="absolute top-0 rounded-sm"
                style={{ left: `${p.left}%`, width: p.size, height: p.size, backgroundColor: p.color }}
                initial={{ y: -24, opacity: 1, rotate: 0 }}
                animate={{ y: "110vh", opacity: [1, 1, 0], rotate: p.rotate }}
                transition={{ duration: p.duration, delay: p.delay, ease: "easeIn" }}
              />
            ))}
          </div>

          <motion.div
            className="relative flex flex-col items-center px-8 text-center"
            initial={{ scale: 0.7, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
          >
            <motion.span
              className="text-7xl"
              initial={{ scale: 0, rotate: -20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
              aria-hidden
            >
              {meta.emoji}
            </motion.span>
            <p className="mt-4 text-xs uppercase tracking-widest text-gold-bright">
              Day {day} milestone
            </p>
            <h2 className="mt-1 font-display text-4xl font-black text-white">{meta.title}</h2>

            <motion.div
              className="mt-4 rounded-full bg-gold/20 px-5 py-2 text-lg font-semibold text-gold-bright"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              🎖 {meta.badge} badge unlocked
            </motion.div>

            <div className="mt-8 flex items-center gap-3">
              <Button onClick={share}>
                <Share2 className="h-4 w-4" /> Share
              </Button>
              <Button variant="secondary" onClick={close}>
                <X className="h-4 w-4" /> Continue
              </Button>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
