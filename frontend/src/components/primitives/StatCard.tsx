import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  accent?: boolean;
}

export function StatCard({ label, value, accent = false }: StatCardProps) {
  return (
    <div
      style={{
        padding: "12px 16px",
        borderRadius: 10,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          fontFamily: "var(--font-mono), monospace",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--text3)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 16,
          fontWeight: 600,
          fontFamily: "var(--font-mono), monospace",
          color: accent ? "var(--accent)" : "var(--text)",
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
    </div>
  );
}
