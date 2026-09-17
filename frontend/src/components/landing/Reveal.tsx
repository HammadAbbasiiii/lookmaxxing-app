"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}

/**
 * Scroll-triggered fade/slide-up. Respects `prefers-reduced-motion`.
 *
 * Under reduced motion the animation is not shortened but *removed* (duration 0,
 * no delay): content should never depend on an entrance playing. The same rule
 * is why the capture helper in `e2e/visual.spec.ts` scrolls the page before
 * screenshotting — a full-page capture that races the IntersectionObserver
 * records a landing page with 35 invisible text blocks that all look fine to a
 * human who scrolls (measured, 2026-09-17).
 */
export function Reveal({ children, className, delay = 0, y = 24 }: RevealProps) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: reduce ? 0 : y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={reduce ? { duration: 0 } : { duration: 0.6, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
