"use client";

import type { EnrichCandidate, FormRequest } from "@/lib/run-types";
import { Button } from "@/components/primitives/Button";

interface DisambiguationChooserProps {
  candidates: EnrichCandidate[];
  onPick: (form: FormRequest) => void;
  onCancel: () => void;
}

export function DisambiguationChooser({
  candidates,
  onPick,
  onCancel,
}: DisambiguationChooserProps) {
  function pick(c: EnrichCandidate) {
    // Prefer linkedin_url (most precise); fall back to name + org.
    const form: FormRequest = c.linkedin_url
      ? { linkedin_url: c.linkedin_url }
      : { name: c.name ?? undefined, company: c.organization ?? undefined };
    onPick(form);
  }

  return (
    <div
      style={{
        padding: 24,
        borderRadius: 14,
        border: "1px solid var(--border)",
        background: "var(--surface)",
        boxShadow: "var(--shadow)",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "var(--font-mono), monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--err)",
            marginBottom: 6,
          }}
        >
          Ambiguous match
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
          We found multiple people — who did you mean?
        </div>
        <div style={{ fontSize: 13, color: "var(--text3)", marginTop: 4 }}>
          Pick one to continue generating the article.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {candidates.map((c, i) => (
          <button
            key={c.apollo_id ?? i}
            onClick={() => pick(c)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 14px",
              borderRadius: 10,
              border: "1px solid var(--border)",
              background: "var(--surface2)",
              color: "var(--text)",
              fontSize: 13,
              cursor: "pointer",
              textAlign: "left",
              transition: "border-color 0.1s, background 0.1s",
              gap: 12,
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={{ fontWeight: 600 }}>{c.name ?? "Unknown"}</span>
              {(c.title || c.organization) && (
                <span style={{ color: "var(--text3)", fontSize: 12 }}>
                  {[c.title, c.organization].filter(Boolean).join(" · ")}
                </span>
              )}
            </div>
            <span style={{ color: "var(--accent)", fontSize: 12, flexShrink: 0 }}>
              Select →
            </span>
          </button>
        ))}
      </div>

      <Button variant="ghost" onClick={onCancel} style={{ alignSelf: "flex-start" }}>
        ← Start over
      </Button>
    </div>
  );
}
