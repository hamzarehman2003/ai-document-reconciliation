import type { NextConfig } from "next";

// /api/* is forwarded to FastAPI by src/proxy.ts (which adds the login token).

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // The proxy holds each request body in memory; uploads can be up to
    // 20 files × 15 MB (the API's limits), so allow that plus form overhead.
    proxyClientMaxBodySize: "310mb",
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
