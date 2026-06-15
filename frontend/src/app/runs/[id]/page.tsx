/**
 * Canonical run view — handles reloads, shared links, and history clicks.
 *
 * This is a Client Component because:
 * - It calls api.getRun() (mutable, cache:'no-store')
 * - RunView needs client-side interactivity (eval trigger, toggle)
 * - Consistent error-handling path shared with the live stream
 *
 * params is consumed via useParams() (Client Component pattern for Next 16 —
 * avoids the async-params Promise which only applies to Server Components).
 */
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { notFound } from "next/navigation";
import { RunView } from "@/components/run/RunView";
import { Spinner } from "@/components/primitives/Spinner";
import { api, ApiError } from "@/lib/api";
import type { Run } from "@/lib/run-types";

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFoundFlag, setNotFoundFlag] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    api
      .getRun(id)
      .then((r) => {
        if (!cancelled) setRun(r);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFoundFlag(true);
        } else {
          // Any other error — treat as not found for simplicity.
          setNotFoundFlag(true);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (notFoundFlag) {
    // Trigger Next.js not-found boundary.
    notFound();
  }

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "40vh",
          gap: 12,
          color: "var(--text3)",
          fontSize: 14,
        }}
      >
        <Spinner size={18} />
        Loading run…
      </div>
    );
  }

  if (!run) return null;

  return (
    <div
      style={{
        maxWidth: 800,
        margin: "0 auto",
        padding: "40px 24px 80px",
        width: "100%",
      }}
    >
      <RunView run={run} onRunUpdated={setRun} />
    </div>
  );
}
