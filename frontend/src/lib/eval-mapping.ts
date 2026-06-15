/**
 * Eval→stage mapping and claim-flagging logic.
 * Pure functions — no React, no side-effects.
 */

import type {
  ClaimGroundedness,
  EvalName,
  EvalReport,
  EvalVerdict,
  Run,
} from "./run-types";
import { evalVerdict, type EvalPillVerdict } from "./status";

// ── Eval → stage map ─────────────────────────────────────────────────────────

/** Which eval (if any) corresponds to each stage. */
const EVAL_FOR_STAGE: Record<string, EvalName | null> = {
  ingest: null,
  enrich: "entity_resolution",
  research: "angle_support",
  draft: "groundedness",
};

/** stage_validity is run-level — shown in RunHeader, not on a single stage row. */
const RUN_LEVEL_EVAL: EvalName = "stage_validity";

export function getVerdictForStage(
  report: EvalReport | null | undefined,
  stageName: string
): EvalVerdict | undefined {
  const evalName = EVAL_FOR_STAGE[stageName];
  if (!evalName || !report) return undefined;
  return report.verdicts.find((v) => v.name === evalName);
}

export function getRunLevelVerdict(
  report: EvalReport | null | undefined
): EvalVerdict | undefined {
  if (!report) return undefined;
  return report.verdicts.find((v) => v.name === RUN_LEVEL_EVAL);
}

export function stagePill(
  report: EvalReport | null | undefined,
  stageName: string
): EvalPillVerdict | null {
  const verdict = getVerdictForStage(report, stageName);
  if (!verdict) return null;
  return evalVerdict(verdict);
}

// ── Summary chip helpers ──────────────────────────────────────────────────────

export interface RunSummary {
  stageCount: number;
  totalDurationMs: number;
  evalsPassCount: number | null; // null = not evaluated
  evalsTotalCount: number | null;
  overallScore: number | null;
}

export function getRunSummary(run: Run): RunSummary {
  const stages = [run.ingest, run.enrich, run.research, run.draft].filter(
    Boolean
  );
  const totalDurationMs = stages.reduce((acc, s) => acc + (s?.duration_ms ?? 0), 0);

  if (!run.evals) {
    return {
      stageCount: stages.length,
      totalDurationMs,
      evalsPassCount: null,
      evalsTotalCount: null,
      overallScore: null,
    };
  }

  const passCount = run.evals.verdicts.filter((v) => v.passed).length;
  return {
    stageCount: stages.length,
    totalDurationMs,
    evalsPassCount: passCount,
    evalsTotalCount: run.evals.verdicts.length,
    overallScore: run.evals.overall_score,
  };
}

// ── Claim flagging ────────────────────────────────────────────────────────────

export interface FlaggedClaim {
  index: number;
  claim: { text: string; source_ids: string[] };
  flagged: boolean;
  reasons: string[];
  supportingSourceIds: string[];
}

/**
 * Flag claims that either cite a missing source ID or were marked unsupported
 * by the groundedness judge.
 *
 * Degrades gracefully: if the groundedness claim-breakdown isn't present
 * (evals not run, or deterministic-only), falls back to source-ID membership
 * checks only.
 */
export function flagClaims(run: Run): FlaggedClaim[] {
  if (!run.article) return [];

  const knownSourceIds = new Set(run.sources.map((s) => s.id));

  // Try to get per-claim groundedness breakdown from the eval report.
  const groundednessVerdict = run.evals?.verdicts.find(
    (v) => v.name === "groundedness"
  );
  const claimBreakdown = extractClaimBreakdown(groundednessVerdict?.details);

  return run.article.claims.map((claim, index) => {
    const reasons: string[] = [];
    let supportingSourceIds: string[] = claim.source_ids;

    // 1. Source-ID membership check
    const missingIds = claim.source_ids.filter((id) => !knownSourceIds.has(id));
    if (missingIds.length > 0) {
      reasons.push(`unknown source${missingIds.length > 1 ? "s" : ""}: ${missingIds.join(", ")}`);
    }

    // 2. Groundedness judge breakdown (if available)
    if (claimBreakdown) {
      const judged = claimBreakdown.find((c) => c.claim_index === index);
      if (judged) {
        supportingSourceIds = judged.supporting_source_ids;
        if (!judged.supported || judged.supporting_source_ids.length === 0) {
          reasons.push("not supported by cited sources");
        }
      }
    }

    return {
      index,
      claim,
      flagged: reasons.length > 0,
      reasons,
      supportingSourceIds,
    };
  });
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function extractClaimBreakdown(
  details: Record<string, unknown> | undefined
): ClaimGroundedness[] | null {
  if (!details) return null;
  const raw = details["claims"];
  if (!Array.isArray(raw)) return null;
  // Validate the first element shape loosely before casting.
  const first = raw[0];
  if (
    typeof first !== "object" ||
    first === null ||
    !("claim_index" in first) ||
    !("supported" in first)
  ) {
    return null;
  }
  return raw as ClaimGroundedness[];
}
