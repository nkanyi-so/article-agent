"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { myRuns } from "@/lib/my-runs";
import type { RunRow } from "@/lib/types";
import { formatDate } from "@/lib/format";

export function Sidebar() {
  const pathname = usePathname();
  const [runs, setRuns] = useState<RunRow[]>([]);
  // The path the list was last loaded for. While it differs from the current
  // path a reload is in flight, so "loading" needs no state of its own.
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const loading = loadedFor !== pathname;

  useEffect(() => {
    let stale = false;
    // In demo mode the list is the seeded runs plus the runs this browser started: on the
    // host each backend instance has its own list, which would change under the visitor.
    Promise.all([api.listRuns(), api.config().catch(() => null)])
      .then(([stored, config]) => {
        if (config?.mode !== "demo") {
          return stored
            .slice()
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        }
        const seeded = stored.filter((run) => run.pinned);
        const mine: RunRow[] = myRuns().map((run) => ({
          id: run.id,
          title: run.title,
          created_at: run.at,
          status: "completed",
          source: run.kind === "re-run" ? "replay" : "seed",
          mode: "demo",
          pinned: false,
          error: null,
          seed_id: null,
          parent_run_id: null,
          replay_from_stage: null,
        }));
        return [...mine, ...seeded];
      })
      .catch((): RunRow[] => [])
      .then((sorted) => {
        if (stale) return;
        setRuns(sorted);
        setLoadedFor(pathname);
      });
    return () => {
      stale = true;
    };
  }, [pathname]);

  return (
    <nav
      className="sidebar"
      aria-label="Runs"
      style={{
        width: 240,
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        background: "var(--bgSub)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Back to the transcripts */}
      <div style={{ padding: "12px 12px 8px", flexShrink: 0 }}>
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: pathname === "/" ? "var(--surface2)" : "var(--surface)",
            color: "var(--text)",
            fontSize: 13,
            fontWeight: 600,
            textDecoration: "none",
            boxSizing: "border-box",
          }}
        >
          <span style={{ fontSize: 15, lineHeight: 1, color: "var(--accent)" }}>
            +
          </span>
          Transcripts
        </Link>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: "var(--border)", flexShrink: 0 }} />

      {/* History section — fills remaining height */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "10px 16px 6px",
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "var(--font-mono), monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text3)",
            flexShrink: 0,
          }}
        >
          Recent runs
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 12px" }}>
          {loading ? (
            // Loading shimmer
            <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "4px 4px" }}>
              {[80, 60, 72].map((w, i) => (
                <div
                  key={i}
                  style={{
                    height: 44,
                    borderRadius: 7,
                    background: "var(--surface)",
                    opacity: 1 - i * 0.2,
                  }}
                />
              ))}
            </div>
          ) : runs.length === 0 ? (
            // Empty state
            <div
              style={{
                padding: "20px 12px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <p
                style={{
                  fontSize: 12,
                  color: "var(--text3)",
                  margin: 0,
                  lineHeight: 1.5,
                }}
              >
                No runs yet.
                <br />
                Generate your first article above.
              </p>
            </div>
          ) : (
            // Run list
            runs.map((run) => {
              const href = `/runs/${run.id}`;
              const active = pathname === href;
              // The part of the title before the colon is the organisation: short enough to scan.
              const label = `${run.title.split(":")[0]}${run.pinned ? "" : run.source === "replay" ? " · re-run" : " · run"}`;
              const statusColor =
                run.status === "completed"
                  ? "var(--pass)"
                  : run.status === "failed"
                  ? "var(--fail)"
                  : "var(--err)";

              return (
                <Link
                  key={run.id}
                  href={href}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 3,
                    padding: "8px 10px",
                    borderRadius: 7,
                    background: active ? "var(--surface2)" : "transparent",
                    border: active
                      ? "1px solid var(--border)"
                      : "1px solid transparent",
                    textDecoration: "none",
                    marginBottom: 2,
                  }}
                >
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--text)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      lineHeight: 1.3,
                    }}
                  >
                    {label}
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{
                        width: 5,
                        height: 5,
                        borderRadius: "50%",
                        background: statusColor,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 11,
                        color: "var(--text3)",
                        fontFamily: "var(--font-mono), monospace",
                      }}
                    >
                      {formatDate(run.created_at)}
                    </span>
                  </div>
                </Link>
              );
            })
          )}
        </div>
      </div>
    </nav>
  );
}
