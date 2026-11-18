import type { NextConfig } from "next";

// On the host, a build without the backend's address would ship a page that calls
// localhost from every visitor's browser. Fail the build instead.
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL must be set for a build on the host.");
}

const nextConfig: NextConfig = {};

export default nextConfig;
