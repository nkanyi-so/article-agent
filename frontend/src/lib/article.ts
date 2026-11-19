/**
 * Turns a stored run into what the screen shows. Pure functions, so the rules a reader
 * relies on (which sentence is flagged, which lines a sentence cites, which question was
 * added by code) are tested without a browser.
 */

import type { Article, EvalReport, RemovedUnit, RunDetail, Segment, Verdict } from "./types";

export type SentenceView = {
  /** Index into the article's claims. */
  index: number;
  text: string;
  /** Flagged by the judge: unsupported even with the question shown. Never set by code. */
  flagged: boolean;
  /** Supported only when read with the question the code added. */
  needsQuestion: boolean;
  /** The judge's reason, when it has given a verdict. */
  reason: string | null;
  judged: boolean;
};

export type Evidence = {
  /** The transcript lines the sentence cites, in transcript order. */
  cited: Segment[];
  /** Added by code, not cited by the model: the question a cited answer replied to. */
  questions: Segment[];
};

const REASONS: Record<RemovedUnit["reason"], string> = {
  no_citation: "It cited no transcript line.",
  invalid_citation: "It cited a transcript line that does not exist.",
  unsupported_number: "A number or date in it is not in the lines it cited",
  unsupported_name: "A name in it is not in the lines it cited",
  misquote: "It quoted words that are not in the lines it cited",
  rests_on_corrected_segment: "It rested on a statement a speaker later corrected",
  wrong_speaker: "It gave a statement to a speaker none of whose lines it cited",
};

/** Why code removed a sentence, in words, with what was missing. */
export function removalReason(unit: RemovedUnit): string {
  const base = REASONS[unit.reason] ?? "It failed a check.";
  if (!unit.detail?.length) return base.endsWith(".") ? base : `${base}.`;
  return `${base.replace(/\.$/, "")}: ${unit.detail.join(", ")}.`;
}

function verdictFor(evaluation: EvalReport | null | undefined, claim: number | null): Verdict | null {
  if (!evaluation || evaluation.judge.outcome !== "judged") return null;
  return evaluation.judge.verdicts?.find((verdict) => verdict.claim === claim) ?? null;
}

/** The article's sentences, grouped into its paragraphs, each with the judge's verdict. */
export function paragraphs(article: Article, evaluation: EvalReport | null | undefined): SentenceView[][] {
  const groups = new Map<number, SentenceView[]>();
  article.claims.forEach((claim, index) => {
    const verdict = verdictFor(evaluation, index);
    const view: SentenceView = {
      index,
      text: claim.text,
      flagged: verdict !== null && !verdict.supported,
      needsQuestion: verdict !== null && verdict.supported && !verdict.supported_alone,
      reason: verdict?.reason || null,
      judged: verdict !== null,
    };
    groups.set(claim.paragraph, [...(groups.get(claim.paragraph) ?? []), view]);
  });
  return [...groups.keys()].sort((a, b) => a - b).map((key) => groups.get(key) ?? []);
}

/** The judge's verdict on the headline, or null when it gave none (a fallback title). */
export function headlineVerdict(evaluation: EvalReport | null | undefined): Verdict | null {
  return verdictFor(evaluation, null);
}

/** The lines behind one sentence. Indexes outside the transcript are dropped, not guessed. */
export function evidenceFor(run: RunDetail, claimIndex: number): Evidence {
  const claim = run.article?.claims[claimIndex];
  if (!claim) return { cited: [], questions: [] };
  const lines = (indexes: number[] | undefined): Segment[] =>
    (indexes ?? [])
      .map((index) => run.segments.find((segment) => segment.index === index))
      .filter((segment): segment is Segment => segment !== undefined);
  return { cited: lines(claim.segment_indexes), questions: lines(claim.question_segments) };
}

export type Flag = {
  claim: number | null;
  text: string;
  reason: string;
  /** Who decided: the judge model, or a code check run after grounding. */
  by: "judge" | "code";
};

/** Every sentence the judge flagged, headline first: what the reader must not miss. */
export function flags(run: RunDetail): Flag[] {
  const { article, evaluation } = run;
  if (!article || !evaluation || evaluation.judge.outcome !== "judged") return [];
  return (evaluation.judge.verdicts ?? [])
    .filter((verdict) => !verdict.supported)
    .map((verdict) => ({
      claim: verdict.claim ?? null,
      text:
        verdict.claim === null || verdict.claim === undefined
          ? article.headline.text
          : (article.claims[verdict.claim]?.text ?? ""),
      reason: verdict.reason || "The judge gave no reason.",
      by: verdict.decided_by === "code" ? ("code" as const) : ("judge" as const),
    }))
    .sort((a, b) => (a.claim ?? -1) - (b.claim ?? -1));
}

export type Scores = {
  kept: number;
  removed: number;
  flagged: number | null;
  withQuestion: number | null;
  alone: number | null;
  codeChecksPassed: boolean | null;
  judgeFailed: string | null;
};

/** The numbers for the score cards. Null means "not measured", never zero. */
export function scores(run: RunDetail): Scores {
  const { article, evaluation } = run;
  const judged = evaluation?.judge.outcome === "judged";
  return {
    kept: article?.claims.length ?? 0,
    removed: article?.removed.length ?? 0,
    flagged: judged ? flags(run).length : null,
    withQuestion: judged ? (evaluation?.judge.score ?? null) : null,
    alone: judged ? (evaluation?.judge.score_alone ?? null) : null,
    codeChecksPassed: evaluation ? evaluation.checks.every((check) => check.passed) : null,
    judgeFailed: evaluation && !judged ? (evaluation.judge.error ?? "unknown") : null,
  };
}

/** True when every recorded model call of the run was replayed from a recording. */
export function replayedFromRecordings(run: RunDetail): boolean {
  return run.model_calls.length > 0 && run.model_calls.every((call) => call.source === "fixture");
}
