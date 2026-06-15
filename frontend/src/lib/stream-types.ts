/**
 * Manual mirror of backend SSE event payload schemas.
 *
 * Per CLAUDE.md convention: update manually when backend/app/schemas.py
 * event models change.
 *
 * Source of truth: backend/app/schemas.py (RunStartedEvent, StageStartedEvent, …)
 */

import type {
  EnrichCandidate,
  FormRequest,
  Run,
  StageOutput,
} from "./run-types";

// ── Event payload types ──────────────────────────────────────────────────────

export interface RunStartedPayload {
  run_id: string;
  created_at: string; // ISO 8601
  input: FormRequest;
}

export interface StageStartedPayload {
  name: string;
}

export interface StageCompletedPayload {
  stage: StageOutput;
}

export interface NeedsDisambiguationPayload {
  run_id: string;
  candidates: EnrichCandidate[];
}

/** Empty payload — emitted before LLM-judge evals run (only when evaluate=true). */
export type EvaluatingPayload = Record<string, never>;

export interface RunCompletedPayload {
  run: Run;
}

export interface RunFailedPayload {
  run: Run;
}

// ── Discriminated union for typed dispatch ───────────────────────────────────

export type PipelineEvent =
  | { event: "run_started"; data: RunStartedPayload }
  | { event: "stage_started"; data: StageStartedPayload }
  | { event: "stage_completed"; data: StageCompletedPayload }
  | { event: "needs_disambiguation"; data: NeedsDisambiguationPayload }
  | { event: "evaluating"; data: EvaluatingPayload }
  | { event: "run_completed"; data: RunCompletedPayload }
  | { event: "run_failed"; data: RunFailedPayload };

// ── Stream handler callbacks (passed to api.streamRun) ──────────────────────

export interface StreamHandlers {
  onRunStarted?: (data: RunStartedPayload) => void;
  onStageStarted?: (data: StageStartedPayload) => void;
  onStageCompleted?: (data: StageCompletedPayload) => void;
  onNeedsDisambiguation?: (data: NeedsDisambiguationPayload) => void;
  onEvaluating?: (data: EvaluatingPayload) => void;
  onCompleted?: (data: RunCompletedPayload) => void;
  onFailed?: (data: RunFailedPayload) => void;
  onError?: (err: Error) => void;
}
