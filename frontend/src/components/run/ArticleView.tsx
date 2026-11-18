import { flagClaims } from "@/lib/eval-mapping";
import { ReferencesList } from "./ReferencesList";
import type { Run } from "@/lib/run-types";

interface ArticleViewProps {
  run: Run;
}

export function ArticleView({ run }: ArticleViewProps) {
  const article = run.article;
  if (!article) return null;

  const flagged = flagClaims(run);
  const flaggedCount = flagged.filter((c) => c.flagged).length;

  const paragraphs = article.body.split(/\n\n+/).filter(Boolean);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {/* Article */}
      <div
        style={{
          padding: 28,
          borderRadius: 14,
          border: "1px solid var(--border)",
          background: "var(--surface)",
          boxShadow: "var(--shadow)",
        }}
      >
        {/* Article header */}
        <div style={{ marginBottom: 20 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text3)",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            Final output
            {flaggedCount > 0 && (
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 5,
                  border: "1px solid color-mix(in srgb, var(--err) 26%, transparent)",
                  background: "color-mix(in srgb, var(--err) 10%, transparent)",
                  color: "var(--err)",
                  fontSize: 10,
                }}
              >
                ⚑ {flaggedCount} claim{flaggedCount > 1 ? "s" : ""} flagged
              </span>
            )}
          </div>
          <h2
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "var(--text)",
              letterSpacing: "-0.02em",
              lineHeight: 1.25,
              margin: 0,
            }}
          >
            {article.title}
          </h2>
        </div>

        {/* Body paragraphs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {paragraphs.map((para, i) => (
            <p
              key={i}
              style={{
                fontSize: 15,
                color: "var(--text)",
                lineHeight: 1.7,
                margin: 0,
              }}
            >
              {para}
            </p>
          ))}
        </div>
      </div>

      {/* Claims panel */}
      {flagged.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text3)",
            }}
          >
            Claims ({flagged.length})
          </div>
          {flagged.map((fc) => (
            <div
              key={fc.index}
              style={{
                padding: "10px 14px",
                borderRadius: 9,
                border: `1px solid ${
                  fc.flagged
                    ? "color-mix(in srgb, var(--err) 30%, transparent)"
                    : "var(--border)"
                }`,
                background: fc.flagged
                  ? "color-mix(in srgb, var(--err) 6%, transparent)"
                  : "var(--surface)",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                {fc.flagged && (
                  <span style={{ color: "var(--err)", flexShrink: 0, fontSize: 13 }}>⚑</span>
                )}
                <p style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.55, margin: 0 }}>
                  {fc.claim.text}
                </p>
              </div>
              {fc.flagged && (
                <div style={{ fontSize: 11, color: "var(--err)", paddingLeft: fc.flagged ? 22 : 0 }}>
                  {fc.reasons.join("; ")}
                </div>
              )}
              {/* Source chips */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, paddingLeft: fc.flagged ? 22 : 0 }}>
                {fc.claim.source_ids.map((id) => {
                  const source = run.sources.find((s) => s.id === id);
                  const isMissing = !source;
                  const isSupported = fc.supportingSourceIds.includes(id);
                  const dotColor = isMissing
                    ? "var(--fail)"
                    : isSupported
                    ? "var(--pass)"
                    : "var(--text3)";
                  return (
                    <span
                      key={id}
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono), monospace",
                        padding: "2px 7px",
                        borderRadius: 5,
                        border: `1px solid ${dotColor}22`,
                        background: `${dotColor}11`,
                        color: isMissing ? "var(--fail)" : "var(--text3)",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <span style={{ width: 5, height: 5, borderRadius: "50%", background: dotColor, display: "inline-block" }} />
                      {source?.title?.slice(0, 40) ?? id}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* References */}
      {run.sources.length > 0 && <ReferencesList sources={run.sources} />}
    </div>
  );
}
