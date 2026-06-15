import { EvalPill } from "@/components/primitives/EvalPill";
import type { EvalVerdict } from "@/lib/run-types";
import { evalVerdict } from "@/lib/status";

interface EvalCardProps {
  verdict: EvalVerdict;
}

export function EvalCard({ verdict }: EvalCardProps) {
  const pill = evalVerdict(verdict);
  const color =
    pill === "pass" ? "var(--pass)" : pill === "warn" ? "var(--err)" : "var(--fail)";

  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: 10,
        border: `1px solid color-mix(in srgb, ${color} 24%, transparent)`,
        background: `color-mix(in srgb, ${color} 7%, transparent)`,
        borderLeft: `3px solid ${color}`,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
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
          {verdict.name.replace(/_/g, " ")}
        </span>
        <EvalPill verdict={pill} mini />
        <span
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono), monospace",
            color: color,
          }}
        >
          {(verdict.score * 100).toFixed(0)}%
        </span>
        <span
          style={{
            fontSize: 10,
            color: "var(--text3)",
            fontFamily: "var(--font-mono), monospace",
          }}
        >
          {verdict.method} · {verdict.confidence} confidence
        </span>
      </div>

      <p style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.55, margin: 0 }}>
        {verdict.reasoning}
      </p>

      {verdict.caveats.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 3 }}>
          {verdict.caveats.map((c, i) => (
            <li key={i} style={{ fontSize: 12, color: "var(--err)" }}>
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
