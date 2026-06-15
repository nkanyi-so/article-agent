import type { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  accent?: boolean;
}

export function Badge({ children, accent = false }: BadgeProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "3px 8px",
        borderRadius: 6,
        border: `1px solid ${accent ? "color-mix(in srgb, var(--accent) 30%, transparent)" : "var(--border)"}`,
        background: accent
          ? "color-mix(in srgb, var(--accent) 10%, transparent)"
          : "var(--surface2)",
        color: accent ? "var(--accent)" : "var(--text2)",
        fontSize: 12,
        fontWeight: 500,
        fontFamily: "var(--font-mono), monospace",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}
