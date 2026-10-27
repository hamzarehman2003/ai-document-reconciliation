import type { NextConfig } from "next";

// Where the FastAPI backend runs. Browser requests to /api/* are forwarded there.
const API_URL = process.env.API_URL ?? "http://localhost:8001";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
