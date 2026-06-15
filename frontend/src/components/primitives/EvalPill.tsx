import type { EvalPillVerdict } from "@/lib/status";
import { EVAL_VERDICT_COLOR_VAR, EVAL_VERDICT_LABEL } from "@/lib/status";

interface EvalPillProps {
  verdict: EvalPillVerdict;
  /** If true, renders as a small squared badge (10px mono) */
  mini?: boolean;
}

export function EvalPill({ verdict, mini = false }: EvalPillProps) {
  const color = EVAL_VERDICT_COLOR_VAR[verdict];
  const label = EVAL_VERDICT_LABEL[verdict];

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: mini ? "2px 6px" : "3px 9px",
        borderRadius: mini ? 5 : 999,
        border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
        background: `color-mix(in srgb, ${color} 14%, transparent)`,
        color,
        fontSize: mini ? 10 : 11,
        fontWeight: 600,
        fontFamily: "var(--font-mono), monospace",
        letterSpacing: "0.04em",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}
