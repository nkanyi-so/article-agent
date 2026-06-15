/**
 * Status → design token mappings.
 *
 * All values are CSS custom property references that resolve correctly
 * in both dark and light themes via the data-theme attribute.
 */

export type StageStatusToken = "ok" | "error" | "pending" | "running";

export const STAGE_STATUS_LABEL: Record<StageStatusToken, string> = {
  pending: "Queued",
  running: "Running",
  ok: "Done",
  error: "Error",
};

export const STAGE_STATUS_COLOR_VAR: Record<StageStatusToken, string> = {
  pending: "var(--text3)",
  running: "var(--run)",
  ok: "var(--pass)",
  error: "var(--fail)",
};

export type EvalPillVerdict = "pass" | "fail" | "warn";

export const EVAL_VERDICT_COLOR_VAR: Record<EvalPillVerdict, string> = {
  pass: "var(--pass)",
  fail: "var(--fail)",
  warn: "var(--err)",
};

export const EVAL_VERDICT_LABEL: Record<EvalPillVerdict, string> = {
  pass: "PASS",
  fail: "FAIL",
  warn: "WARN",
};

/**
 * Derive the display verdict for an EvalVerdict.
 * warn = degraded OR low confidence.
 */
export function evalVerdict(v: {
  passed: boolean;
  degraded: boolean;
  confidence: string;
}): EvalPillVerdict {
  if (v.degraded || v.confidence === "low") return "warn";
  return v.passed ? "pass" : "fail";
}
