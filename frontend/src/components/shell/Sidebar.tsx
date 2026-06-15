"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Run } from "@/lib/run-types";
import { formatDate } from "@/lib/format";

interface SidebarProps {
  runs: Run[];
}

export function Sidebar({ runs }: SidebarProps) {
  const pathname = usePathname();

  return (
    <nav
      style={{
        width: 240,
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        background: "var(--bgSub)",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* New article button */}
      <div style={{ padding: "12px 12px 8px" }}>
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
            transition: "background 0.12s",
          }}
        >
          <span style={{ fontSize: 16, lineHeight: 1 }}>＋</span>
          New article
        </Link>
      </div>

      {/* History */}
      {runs.length > 0 && (
        <>
          <div
            style={{
              padding: "8px 16px 4px",
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text3)",
            }}
          >
            Recent runs
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 12px" }}>
            {runs.map((run) => {
              const href = `/runs/${run.id}`;
              const active = pathname.startsWith(`/runs/${run.id}`);
              const label =
                run.article?.title ??
                run.input.name ??
                run.input.linkedin_url ??
                run.id.slice(0, 8);
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
                    gap: 2,
                    padding: "8px 10px",
                    borderRadius: 7,
                    background: active ? "var(--surface2)" : "transparent",
                    border: active ? "1px solid var(--border)" : "1px solid transparent",
                    textDecoration: "none",
                    transition: "background 0.1s",
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
            })}
          </div>
        </>
      )}
    </nav>
  );
}
