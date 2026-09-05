import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The build must never fail on lint rules while the codebase is being
  // scaffolded; TypeScript is still fully enforced by `next build`.
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      // Cloudinary delivers all user photos (results, progress, explore).
      { protocol: "https", hostname: "res.cloudinary.com" },
    ],
  },
  // Defense-in-depth headers (§19). Kept conservative on purpose: no CSP here
  // because Next.js hydrates with inline scripts and a strict CSP without a
  // per-request nonce would break the app. These four are safe everywhere.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
