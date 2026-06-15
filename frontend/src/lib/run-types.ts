/**
 * Manual mirror of backend Pydantic models.
 *
 * Per CLAUDE.md convention: when a backend response shape changes, update
 * this file manually. These types are NOT generated.
 *
 * Source of truth: backend/app/schemas.py + backend/app/evals/schemas.py
 */

// ── Primitives ──────────────────────────────────────────────────────────────

export type SourceKind = "apollo" | "exa";

export interface Source {
  id: string;
  kind: SourceKind;
  url: string | null;
  title: string | null;
  snippet: string | null;
  retrieved_at: string; // ISO 8601
}

export interface StageError {
  code: string;
  message: string;
  retryable: boolean;
  http_status: number;
}

export interface StageOutput {
  name: string;
  status: "ok" | "error";
  duration_ms: number;
  sources: Source[];
  /** Typed as unknown; narrow by stage name using the type guards below. */
  output: unknown;
  error: StageError | null;
}

// ── Stage output shapes (narrow StageOutput.output by stage name) ───────────

export interface Brief {
  name: string | null;
  linkedin_url: string | null;
  company: string | null;
  display_name: string;
  search_terms: string[];
}

export interface PersonFacts {
  apollo_id: string | null;
  name: string | null;
  title: string | null;
  organization: string | null;
  organization_domain: string | null;
  linkedin_url: string | null;
  location: string | null;
  raw: Record<string, unknown>;
}

export interface EnrichCandidate {
  apollo_id: string | null;
  name: string | null;
  title: string | null;
  organization: string | null;
  linkedin_url: string | null;
  confidence: number | null;
}

export interface EnrichResult {
  status: "matched" | "ambiguous";
  person: PersonFacts | null;
  candidates: EnrichCandidate[];
}

export interface ChosenAngle {
  headline: string;
  angle: string;
  rationale: string;
  supporting_source_ids: string[];
}

export interface ResearchResult {
  angle: ChosenAngle;
  sources: Source[];
}

export interface Claim {
  text: string;
  source_ids: string[];
}

export interface DraftArticle {
  title: string;
  body: string;
  claims: Claim[];
}

export interface DraftResult {
  article: DraftArticle;
  claim_source_map: Record<string, string[]>;
  sources: Source[];
}

// ── Stage output type guards ─────────────────────────────────────────────────

export function isBrief(output: unknown): output is Brief {
  return (
    typeof output === "object" &&
    output !== null &&
    "display_name" in output &&
    "search_terms" in output
  );
}

export function isEnrichResult(output: unknown): output is EnrichResult {
  return (
    typeof output === "object" &&
    output !== null &&
    "status" in output &&
    ((output as EnrichResult).status === "matched" ||
      (output as EnrichResult).status === "ambiguous")
  );
}

export function isResearchResult(output: unknown): output is ResearchResult {
  return (
    typeof output === "object" &&
    output !== null &&
    "angle" in output &&
    typeof (output as ResearchResult).angle === "object"
  );
}

export function isDraftResult(output: unknown): output is DraftResult {
  return (
    typeof output === "object" &&
    output !== null &&
    "article" in output &&
    "claim_source_map" in output
  );
}

// ── Evals ────────────────────────────────────────────────────────────────────

export type EvalName =
  | "groundedness"
  | "entity_resolution"
  | "angle_support"
  | "stage_validity";

export interface EvalVerdict {
  name: EvalName;
  score: number;
  passed: boolean;
  reasoning: string;
  method: "deterministic" | "llm_judge";
  confidence: "high" | "medium" | "low";
  degraded: boolean;
  caveats: string[];
  details: Record<string, unknown>;
}

export interface EvalReport {
  overall_score: number;
  passed: boolean;
  complete: boolean;
  verdicts: EvalVerdict[];
  degraded: boolean;
  caveats: string[];
  evaluated_at: string; // ISO 8601
  judge_model: string | null;
}

// ── Claim groundedness detail (inside EvalVerdict.details for groundedness) ──

export interface ClaimGroundedness {
  claim_index: number;
  claim_text: string;
  supported: boolean;
  cited_source_ids: string[];
  supporting_source_ids: string[];
  reasoning: string;
}

// ── Run ──────────────────────────────────────────────────────────────────────

export type RunStatus =
  | "completed"
  | "failed"
  | "needs_disambiguation";

export interface FormRequest {
  name?: string | null;
  linkedin_url?: string | null;
  company?: string | null;
}

export interface Run {
  id: string;
  created_at: string; // ISO 8601
  input: FormRequest;
  status: RunStatus;
  ingest: StageOutput;
  enrich: StageOutput;
  research: StageOutput | null;
  draft: StageOutput | null;
  article: DraftArticle | null;
  claim_source_map: Record<string, string[]> | null;
  sources: Source[];
  error: StageError | null;
  evals: EvalReport | null;
}

// ── API response wrappers ────────────────────────────────────────────────────

export interface RunResponse {
  run: Run;
}

export interface RunsResponse {
  runs: Run[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
