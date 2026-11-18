/** Summary chip — value over a small label, used in RunHeader. */

import type { ReactNode } from "react";

interface ChipProps {
  label: string;
  value: ReactNode;
  valueColor?: string;
}

export function Chip({ label, value, valueColor }: ChipProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "6px 12px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--surface2)",
        gap: 2,
        minWidth: 60,
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: valueColor ?? "var(--text)",
          fontFamily: "var(--font-mono), monospace",
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          fontFamily: "var(--font-mono), monospace",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: "var(--text3)",
        }}
      >
        {label}
      </div>
    </div>
  );
}
