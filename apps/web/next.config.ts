import type { NextConfig } from "next";

const backendUrl =
  process.env.BACKEND_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://dayleaf-api.onrender.com"
    : "http://127.0.0.1:8000");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  experimental: { cpus: 1, webpackBuildWorker: false },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
