import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

interface TopBarProps {
  runId?: string | null;
}

export function TopBar({ runId }: TopBarProps) {
  return (
    <header
      style={{
        height: 56,
        padding: "0 20px",
        borderBottom: "1px solid var(--border)",
        background: "var(--bgSub)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        flexShrink: 0,
        zIndex: 10,
        position: "sticky",
        top: 0,
      }}
    >
      {/* Brand — links home */}
      <Link
        href="/"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          textDecoration: "none",
        }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 7,
            background: "var(--accent)",
            boxShadow: "0 0 0 4px color-mix(in srgb, var(--accent) 20%, transparent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            fontWeight: 700,
            fontFamily: "var(--font-mono), monospace",
            color: "var(--accentText)",
            flexShrink: 0,
          }}
        >
          A
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
            Article Agent
          </span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text3)",
            }}
          >
            Grounded articles
          </span>
        </div>
      </Link>

      <div style={{ flex: 1 }} />

      {/* Run ID badge — only on run pages */}
      {runId && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--surface)",
          }}
        >
          <span
            style={{
              fontSize: 11,
              color: "var(--text3)",
              fontFamily: "var(--font-mono), monospace",
            }}
          >
            run
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text2)",
              fontFamily: "var(--font-mono), monospace",
            }}
          >
            {runId.slice(0, 8)}
          </span>
        </div>
      )}

      <ThemeToggle />
    </header>
  );
}
