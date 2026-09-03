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
};

export default nextConfig;
