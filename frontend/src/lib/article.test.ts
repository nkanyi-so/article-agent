import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { messageFor } from "./api";
import {
  evidenceFor,
  flags,
  headlineVerdict,
  paragraphs,
  removalReason,
  replayedFromRecordings,
  scores,
  stageSummary,
} from "./article";
import { CLAIM, linkMayStartRuns } from "./copy";
import type { RunDetail } from "./types";

const segment = (index: number, speaker: string, text: string) => ({ index, turn: index, speaker, line: index + 1, text });
const claim = (text: string, paragraph: number, cited: number[], questions: number[] = []) => ({
  text,
  paragraph,
  citations: cited.map((i) => ({ start_segment: i, end_segment: i + 1, cited_text: "" })),
  segment_indexes: cited,
  name_resolutions: [],
  question_segments: questions,
});
const verdict = (c: number | null, supported: boolean, alone: boolean, reason: string) => ({
  claim: c,
  supported,
  supported_alone: alone,
  decided_by: "judge" as const,
  supporting_segments: [],
  reason,
});

/** A run written by hand: three kept sentences, one removed, one flagged. */
function run(overrides: Partial<RunDetail> = {}): RunDetail {
  return {
    run: { id: "r1", title: "Harbour committee: March meeting", status: "completed", source: "seed", mode: "demo", created_at: "2026-11-19T06:00:00+00:00", pinned: true, error: null, seed_id: "s", parent_run_id: null, replay_from_stage: null },
    cost_usd: 0.07,
    stages: [],
    model_calls: [{ stage: "extract", source: "fixture", cost_usd: 0.02 }, { stage: "draft", source: "fixture", cost_usd: 0.05 }] as RunDetail["model_calls"],
    segments: [
      segment(0, "Ana Ruiz", "How long was the bridge closed?"),
      segment(1, "Leo Brandt", "Six weeks."),
      segment(2, "Leo Brandt", "It reopened in May."),
      segment(3, "Ana Ruiz", "The repair cost 40,000 pounds."),
    ],
    article: {
      headline: { text: "Bridge reopens after six weeks", source: "model", supporting_claims: [0], failure_detail: [] },
      claims: [
        claim("Brandt said the bridge was closed for six weeks.", 0, [1], [0]),
        claim("It reopened in May.", 0, [2]),
        claim("Ruiz, who chaired, said the repair cost 40,000 pounds.", 1, [3]),
      ],
      removed: [{ text: "The repair cost 45,000 pounds.", paragraph: 1, reason: "unsupported_number", detail: ["45,000"], segment_indexes: [3] }],
    },
    evaluation: {
      checks: [{ id: "E1", name: "", passed: true, score: 1, detail: [] }],
      judge: {
        outcome: "judged",
        model: "claude-opus-5-5",
        score: 0.75,
        score_alone: 0.5,
        verdicts: [
          verdict(0, true, false, "Stated, read with the question."),
          verdict(1, true, true, "Stated."),
          verdict(2, false, false, "No line says Ruiz chaired."),
          verdict(null, true, true, "Stated."),
        ],
      },
      drafted: 4,
      removed: 1,
      removal_rate: 0.25,
    },
    ...overrides,
  } as RunDetail;
}

describe("the article's sentences", () => {
  it("are grouped into paragraphs in order, each with its claim index", () => {
    const view = paragraphs(run().article!, run().evaluation);
    expect(view.map((p) => p.map((s) => s.index))).toEqual([[0, 1], [2]]);
  });

  it("mark as flagged only what the judge found unsupported, with its reason", () => {
    const sentences = paragraphs(run().article!, run().evaluation).flat();
    expect(sentences.map((s) => s.flagged)).toEqual([false, false, true]);
    expect(sentences[2]?.reason).toBe("No line says Ruiz chaired.");
    expect(sentences[0]?.needsQuestion).toBe(true);
    expect(sentences[1]?.needsQuestion).toBe(false);
  });

  it("flag nothing when the judge could not be used: that is not a verdict", () => {
    const failed = run({ evaluation: { ...run().evaluation!, judge: { outcome: "failed", error: "model_refused", verdicts: [] } } as RunDetail["evaluation"] });
    expect(paragraphs(failed.article!, failed.evaluation).flat().some((s) => s.flagged || s.judged)).toBe(false);
    expect(flags(failed)).toEqual([]);
    expect(scores(failed)).toMatchObject({ flagged: null, withQuestion: null, judgeFailed: "model_refused" });
  });

  it("flag nothing on a run that was never evaluated", () => {
    const bare = run({ evaluation: null });
    expect(paragraphs(bare.article!, null).flat().every((s) => !s.flagged)).toBe(true);
    expect(scores(bare).codeChecksPassed).toBeNull();
  });
});

describe("the lines behind a sentence", () => {
  it("are the cited lines, and apart from them the question that code added", () => {
    const evidence = evidenceFor(run(), 0);
    expect(evidence.cited.map((s) => s.text)).toEqual(["Six weeks."]);
    expect(evidence.questions.map((s) => s.text)).toEqual(["How long was the bridge closed?"]);
  });

  it("have no question when the code added none", () => {
    expect(evidenceFor(run(), 1).questions).toEqual([]);
  });

  it("drop an index outside the transcript instead of showing another line", () => {
    const broken = run();
    broken.article!.claims[1]!.segment_indexes = [2, 99];
    expect(evidenceFor(broken, 1).cited.map((s) => s.index)).toEqual([2]);
    expect(evidenceFor(broken, 42)).toEqual({ cited: [], questions: [] });
  });
});

describe("removed and flagged are different lists", () => {
  it("lists what the judge flagged, with the judge's reason, and not what code removed", () => {
    expect(flags(run())).toEqual([
      { claim: 2, text: "Ruiz, who chaired, said the repair cost 40,000 pounds.", reason: "No line says Ruiz chaired.", by: "judge" },
    ]);
  });

  it("says when it was a code check, not the judge, that marked a kept sentence", () => {
    const checked = run();
    checked.evaluation!.judge.verdicts![1] = { ...verdict(1, false, false, "Failed a code check."), decided_by: "code" };
    expect(flags(checked).map((f) => [f.claim, f.by])).toEqual([[1, "code"], [2, "judge"]]);
  });

  it("puts a flagged headline first", () => {
    const flagged = run();
    flagged.evaluation!.judge.verdicts![3] = verdict(null, false, false, "Nobody said it reopened.");
    expect(flags(flagged).map((f) => f.claim)).toEqual([null, 2]);
    expect(flags(flagged)[0]?.text).toBe("Bridge reopens after six weeks");
    expect(headlineVerdict(flagged.evaluation)?.supported).toBe(false);
  });

  it("says in words why code removed a sentence, with what was missing", () => {
    expect(removalReason(run().article!.removed[0]!)).toBe("A number or date in it is not in the lines it cited: 45,000.");
    expect(removalReason({ text: "", paragraph: 0, reason: "no_citation", detail: [], segment_indexes: [] })).toBe("It cited no transcript line.");
  });
});

describe("the scores", () => {
  it("count kept, removed and flagged, and give both judged shares", () => {
    expect(scores(run())).toEqual({ kept: 3, removed: 1, flagged: 1, withQuestion: 0.75, alone: 0.5, codeChecksPassed: true, judgeFailed: null });
  });

  it("know a run replayed from recordings from one that called a model", () => {
    expect(replayedFromRecordings(run())).toBe(true);
    const live = run();
    live.model_calls[0]!.source = "live";
    expect(replayedFromRecordings(live)).toBe(false);
    expect(replayedFromRecordings(run({ model_calls: [] }))).toBe(false);
  });
});

describe("a link that starts a run by itself", () => {
  it("is honoured only when the server says it replays recordings", () => {
    expect(linkMayStartRuns({ mode: "demo" })).toBe(true);
    expect(linkMayStartRuns({ mode: "live" })).toBe(false);
    expect(linkMayStartRuns(null)).toBe(false);
  });

  it("shows the claim word for word as the decision record has it", () => {
    const record = readFileSync(new URL("../../../docs/decisions/0015-the-claim.md", import.meta.url), "utf8");
    expect(record).toContain(`> ${CLAIM}`);
  });
});

describe("error messages", () => {
  it("say what happened for a known code, and never echo an unknown one", () => {
    expect(messageFor("run_not_found")).toBe("There is no run with this address.");
    expect(messageFor("network")).toBe("The backend could not be reached.");
    expect(messageFor("<script>")).toBe("Something went wrong on the server.");
    expect(messageFor(null)).toBe("Something went wrong on the server.");
  });
});

describe("a stage's summary", () => {
  it("says in words what each stage produced", () => {
    expect(stageSummary({ name: "ingest", output: { segments: [{ speaker: "A" }, { speaker: "B" }, { speaker: "A" }] } })).toBe(
      "Split into 3 numbered lines from 2 speakers."
    );
    expect(stageSummary({ name: "extract", output: { points: [1, 2], corrections: [1], disagreements: [] } })).toBe(
      "Listed 2 points, 1 correction and 0 disagreements."
    );
    expect(stageSummary({ name: "ground", output: { headline: { source: "title" }, claims: [1, 2, 3], removed: [1] } })).toBe(
      "Kept 3 sentences, removed 1; the headline replaced by the title."
    );
    expect(
      stageSummary({
        name: "evaluate",
        output: { checks: [{ passed: true }, { passed: true }], judge: { outcome: "judged", verdicts: [{ supported: false }, { supported: true }] } },
      })
    ).toBe("2 of 2 code checks passed; the judge flagged 1.");
    expect(stageSummary({ name: "evaluate", output: { checks: [], judge: { outcome: "failed" } } })).toBe(
      "0 of 0 code checks passed; the judge could not be used."
    );
  });

  it("gives nothing, not something wrong, for a record it cannot read", () => {
    expect(stageSummary({ name: "ingest", output: null })).toBeNull();
    expect(stageSummary({ name: "ingest", output: { segments: "no" } })).toBeNull();
    expect(stageSummary({ name: "publish", output: {} })).toBeNull();
  });
});
