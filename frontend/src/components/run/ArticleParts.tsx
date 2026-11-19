import type { ReactNode } from "react";
import { StatCard } from "@/components/primitives/StatCard";
import {
  evidenceFor,
  flags,
  headlineVerdict,
  paragraphs,
  removalReason,
  scores,
} from "@/lib/article";
import type { RunDetail, Segment } from "@/lib/types";

/** What is chosen: a sentence by its index, the headline, or nothing. */
export type Selection = number | "headline" | null;

/**
 * A sentence the reader can choose. A span with a button's role, not a `<button>`: a
 * button cannot wrap across lines, and a sentence has to flow as text.
 */
function Choosable({
  pressed,
  flagged,
  label,
  onChoose,
  children,
  style,
}: {
  pressed?: boolean;
  flagged: boolean;
  label?: string;
  onChoose: () => void;
  children: ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <span
      role="button"
      tabIndex={0}
      className={`sentence${flagged ? " flagged" : ""}`}
      aria-pressed={pressed}
      aria-label={label}
      onClick={onChoose}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onChoose();
        }
      }}
      style={style}
    >
      {children}
    </span>
  );
}

function Heading({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <h2 className="micro" style={{ margin: "0 0 10px", display: "flex", gap: 8 }}>
      <span>{children}</span>
      {count !== undefined && <span style={{ color: "var(--text2)" }}>{count}</span>}
    </h2>
  );
}

export function ScoreCards({ run }: { run: RunDetail }) {
  const s = scores(run);
  const share = (value: number | null): string =>
    value === null ? "not judged" : `${Math.round(value * 100)}%`;
  return (
    <section aria-label="Scores">
      <div className="score-row">
        <StatCard label="Sentences kept" value={s.kept} />
        <StatCard
          label="Removed by code"
          value={<span style={{ color: s.removed ? "var(--fail)" : undefined }}>{s.removed}</span>}
        />
        <StatCard
          label="Flagged by the judge"
          value={
            <span style={{ color: s.flagged ? "var(--err)" : undefined }}>
              {s.flagged ?? "not judged"}
            </span>
          }
        />
        <StatCard label="Judged supported" value={share(s.withQuestion)} accent />
      </div>
      <p style={{ margin: "10px 2px 0", fontSize: 12.5, color: "var(--text3)", lineHeight: 1.6 }}>
        {s.judgeFailed
          ? `The judge could not be used on this run (${s.judgeFailed}), so nothing is flagged and no score is shown. That is a failure of the machinery, not a verdict.`
          : s.withQuestion === null
            ? "This run was not evaluated."
            : `Judged supported counts each sentence and the headline, reading an answer together with the question it replied to. With the cited lines entirely alone it is ${share(s.alone)}. Code checks on this run: ${s.codeChecksPassed ? "all passed" : "one or more failed"}.`}
      </p>
    </section>
  );
}

export function ArticlePanel({
  run,
  selected,
  onSelect,
}: {
  run: RunDetail;
  selected: Selection;
  onSelect: (selection: Selection) => void;
}) {
  const article = run.article;
  if (!article) return null;
  const headline = headlineVerdict(run.evaluation);
  const headlineFlagged = headline !== null && !headline.supported;
  return (
    <article className="panel" style={{ padding: "22px 24px" }}>
      <Heading>The article · choose a sentence to see the lines behind it</Heading>
      <h1 style={{ fontSize: 22, lineHeight: 1.3, letterSpacing: "-0.01em", margin: "0 0 14px" }}>
        <Choosable
          flagged={headlineFlagged}
          pressed={selected === "headline"}
          onChoose={() => onSelect(selected === "headline" ? null : "headline")}
        >
          {article.headline.text}
        </Choosable>
        {headlineFlagged && <span className="flag-mark">flagged</span>}
      </h1>
      {paragraphs(article, run.evaluation).map((sentences, position) => (
        <p key={position} style={{ fontSize: 15.5, lineHeight: 1.75, margin: "0 0 14px" }}>
          {sentences.map((sentence) => (
            <span key={sentence.index}>
              <Choosable
                flagged={sentence.flagged}
                pressed={selected === sentence.index}
                label={`${sentence.text}${sentence.flagged ? " (flagged by the judge)" : ""}`}
                onChoose={() => onSelect(selected === sentence.index ? null : sentence.index)}
              >
                {sentence.text}
              </Choosable>
              {sentence.flagged && <span className="flag-mark">flagged</span>}{" "}
            </span>
          ))}
        </p>
      ))}
    </article>
  );
}

function Line({ segment, question = false }: { segment: Segment; question?: boolean }) {
  return (
    <div className={`line${question ? " question" : ""}`}>
      <div className="micro" style={{ marginBottom: 3 }}>
        line {segment.index} · {segment.speaker}
      </div>
      <div style={{ fontSize: 14, lineHeight: 1.55 }}>{segment.text}</div>
    </div>
  );
}

export function EvidencePanel({
  run,
  selected,
  onClose,
}: {
  run: RunDetail;
  selected: Selection;
  onClose: () => void;
}) {
  const open = selected !== null;
  let body: ReactNode;
  if (selected === null) {
    body = (
      <p style={{ margin: 0, color: "var(--text2)", lineHeight: 1.6 }}>
        Choose any sentence of the article. The transcript lines it cites appear here, word for
        word, with what the judge model said about it.
      </p>
    );
  } else if (selected === "headline") {
    const verdict = headlineVerdict(run.evaluation);
    const fallback = run.article?.headline.source === "title";
    body = (
      <div style={{ display: "grid", gap: 10 }}>
        <p style={{ margin: 0, color: "var(--text2)", lineHeight: 1.6 }}>
          {fallback
            ? "This is the transcript's own title. The model's headline failed the code check and was thrown away, so the title is used and the judge is not asked about it."
            : "A headline cites no lines of its own. Code checks that its names and figures appear in sentences that were kept; the judge reads it against the lines of the whole kept article."}
        </p>
        {fallback && run.article?.headline.rejected_text && (
          <div className="note-removed">
            <div className="micro" style={{ color: "var(--fail)", marginBottom: 4 }}>
              The model&apos;s headline, removed by code
            </div>
            {run.article.headline.rejected_text}
          </div>
        )}
        {verdict && <JudgeNote supported={verdict.supported} alone={verdict.supported_alone ?? false} reason={verdict.reason ?? ""} hasQuestion={false} />}
      </div>
    );
  } else {
    const { cited, questions } = evidenceFor(run, selected);
    const verdict = run.evaluation?.judge.verdicts?.find((v) => v.claim === selected) ?? null;
    body = (
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ fontSize: 14, lineHeight: 1.55, color: "var(--text2)" }}>
          “{run.article?.claims[selected]?.text}”
        </div>
        <div className="micro">Cited by the model · {cited.length} {cited.length === 1 ? "line" : "lines"}</div>
        {cited.map((segment) => (
          <Line key={segment.index} segment={segment} />
        ))}
        {questions.length > 0 && (
          <>
            <div className="micro">
              Added by code, not cited by the model · the question being answered · not evidence
            </div>
            {questions.map((segment) => (
              <Line key={segment.index} segment={segment} question />
            ))}
          </>
        )}
        {verdict ? (
          <JudgeNote
            byCode={verdict.decided_by === "code"}
            supported={verdict.supported}
            alone={verdict.supported_alone ?? false}
            reason={verdict.reason ?? ""}
            hasQuestion={questions.length > 0}
          />
        ) : (
          <p style={{ margin: 0, color: "var(--text3)", fontSize: 13 }}>The judge gave no verdict on this sentence.</p>
        )}
      </div>
    );
  }
  return (
    <aside className={`panel evidence ${open ? "open" : "idle"}`} aria-label="The lines behind the chosen sentence">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <h2 className="micro" style={{ margin: 0 }}>The transcript lines behind it</h2>
        <button
          type="button"
          className="evidence-close link"
          onClick={onClose}
          style={{ background: "none", border: 0, cursor: "pointer", fontSize: 13 }}
        >
          Close
        </button>
      </div>
      {body}
    </aside>
  );
}

function JudgeNote({
  byCode = false,
  supported,
  alone,
  reason,
  hasQuestion,
}: {
  byCode?: boolean;
  supported: boolean;
  alone: boolean;
  reason: string;
  hasQuestion: boolean;
}) {
  if (!supported) {
    return (
      <div className="note-flag">
        <div className="micro" style={{ color: "var(--err)", marginBottom: 4 }}>
          {byCode ? "Failed a code check after grounding" : "Flagged by the judge model"} · kept in
          the article
        </div>
        <div style={{ lineHeight: 1.55 }}>{reason || "The judge gave no reason."}</div>
      </div>
    );
  }
  return (
    <div className="note-ok">
      <div className="micro" style={{ color: "var(--pass)", marginBottom: 4 }}>
        Judge model: supported{hasQuestion && !alone ? ", but only with the question shown" : ""}
      </div>
      <div style={{ lineHeight: 1.55 }}>{reason}</div>
    </div>
  );
}

export function FlagList({ run, onSelect }: { run: RunDetail; onSelect: (selection: Selection) => void }) {
  const found = flags(run);
  return (
    <section className="panel">
      <Heading count={found.length}>Flagged · still in the article</Heading>
      {found.length === 0 ? (
        <p style={{ margin: 0, color: "var(--text2)" }}>
          {run.evaluation?.judge.outcome === "judged"
            ? "The judge found every sentence supported by the lines it cites."
            : "The judge did not run on this article."}
        </p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
          {found.map((flag) => (
            <li key={flag.claim ?? "headline"} className="note-flag">
              <div style={{ marginBottom: 4, lineHeight: 1.55 }}>
                <Choosable flagged onChoose={() => onSelect(flag.claim ?? "headline")}>
                  {flag.claim === null ? `Headline: ${flag.text}` : flag.text}
                </Choosable>
              </div>
              <div style={{ color: "var(--text2)", fontSize: 13, lineHeight: 1.55 }}>
                <span style={{ color: "var(--err)", fontWeight: 600 }}>
                  {flag.by === "code" ? "Code check after grounding: " : "Judge: "}
                </span>
                {flag.reason}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function RemovedList({ run }: { run: RunDetail }) {
  const removed = run.article?.removed ?? [];
  return (
    <section className="panel">
      <Heading count={removed.length}>Removed by code · not in the article</Heading>
      {removed.length === 0 ? (
        <p style={{ margin: 0, color: "var(--text2)" }}>
          Code removed nothing: every sentence the model drafted had its numbers, dates, names and
          quotations in the lines it cited.
        </p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
          {removed.map((unit, position) => (
            <li key={position} className="note-removed">
              <div style={{ textDecoration: "line-through", textDecorationColor: "var(--fail)", lineHeight: 1.55 }}>
                {unit.text}
              </div>
              <div style={{ color: "var(--text2)", fontSize: 13, marginTop: 4, lineHeight: 1.55 }}>
                <span style={{ color: "var(--fail)", fontWeight: 600 }}>Code: </span>
                {removalReason(unit)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
