"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type BackendHealth } from "@/lib/health";

/**
 * Shows whether the browser can reach the backend, and which mode it is in.
 * The request is made from the browser on purpose: it only succeeds if the
 * backend's CORS settings allow this page's origin.
 */
export function BackendStatus() {
  const [health, setHealth] = useState<BackendHealth | null>(null);

  useEffect(() => {
    let stale = false;
    fetchHealth().then((result) => {
      if (!stale) setHealth(result);
    });
    return () => {
      stale = true;
    };
  }, []);

  const label =
    health === null
      ? "API …"
      : health.reachable
        ? `API ${health.mode} · ${health.version}`
        : "API unreachable";
  const dot =
    health === null ? "var(--text3)" : health.reachable ? "var(--pass)" : "var(--fail)";

  return (
    <div
      data-testid="backend-status"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        color: "var(--text3)",
        fontFamily: "var(--font-mono), monospace",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: dot }} />
      {label}
    </div>
  );
}
