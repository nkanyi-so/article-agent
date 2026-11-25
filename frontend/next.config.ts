import type { NextConfig } from "next";

// On the host, a build without the backend's address would ship a page that calls
// localhost from every visitor's browser. Fail the build instead.
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL must be set for a build on the host.");
}

// Sent on every route. No X-Frame-Options, frame-ancestors or Content-Security-Policy
// here: the site is meant to be embedded in another page.
const securityHeaders: { key: string; value: string }[] = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
