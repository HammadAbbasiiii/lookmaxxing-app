import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Inter, Space_Grotesk } from "next/font/google";
import { Providers } from "@/components/providers";
import { AnalyticsTracker } from "@/components/AnalyticsTracker";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LookMaxx — What's your score?",
  description:
    "Upload one photo. Get your baseline score and a 90-day plan to improve it. Free, private, and yours forever.",
  keywords: ["looksmaxxing", "face analysis", "skincare", "grooming", "90-day plan"],
};

// `viewportFit: "cover"` is what makes env(safe-area-inset-*) non-zero on
// iPhone 14/15/16 (notch + Dynamic Island) when the app is installed to the
// home screen or run in standalone mode. Without it the safe-area padding in
// TopNav/BottomNav silently collapses to 0.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0a0a0a",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable}`}
      data-scroll-behavior="smooth"
    >
      <body>
        <AnalyticsTracker />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
