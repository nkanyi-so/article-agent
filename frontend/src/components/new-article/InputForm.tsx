"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/primitives/Button";
import { SegmentedControl } from "@/components/primitives/SegmentedControl";
import type { FormRequest } from "@/lib/run-types";

interface InputFormProps {
  onSubmit: (form: FormRequest, evaluate: boolean) => void;
  disabled?: boolean;
}

type EntryTab = "name" | "transcript";

function isLinkedInUrl(s: string) {
  // Matches www and country subdomains (uk.linkedin.com, fr.linkedin.com, etc.)
  return /^https?:\/\/([\w-]+\.)?linkedin\.com\//i.test(s) || s.startsWith("linkedin.com/");
}

export function InputForm({ onSubmit, disabled = false }: InputFormProps) {
  const [tab, setTab] = useState<EntryTab>("name");
  const [input, setInput] = useState("");
  const [company, setCompany] = useState("");
  const [evaluate, setEvaluate] = useState(false);

  const isUrl = isLinkedInUrl(input.trim());
  const inputTag = input.trim() ? (isUrl ? "LinkedIn URL" : "Name") : null;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    const form: FormRequest = isUrl
      ? { linkedin_url: trimmed, company: company.trim() || null }
      : { name: trimmed, company: company.trim() || null };
    onSubmit(form, evaluate);
  }

  const canSubmit = Boolean(input.trim()) && !disabled && tab === "name";

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {/* Entry sub-tabs */}
      <SegmentedControl
        options={[
          { value: "name" as EntryTab, label: "From a name" },
          { value: "transcript" as EntryTab, label: "Paste a transcript" },
        ]}
        value={tab}
        onChange={setTab}
      />

      <div style={{ height: 20 }} />

      {tab === "transcript" ? (
        // Disabled "coming soon" panel
        <div
          style={{
            padding: "40px 32px",
            borderRadius: 14,
            border: "1.5px dashed var(--border2)",
            background: "var(--surface)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 28, lineHeight: 1 }}>📋</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text2)" }}>
            Transcript entry coming soon
          </div>
          <div style={{ fontSize: 13, color: "var(--text3)", maxWidth: 320 }}>
            Paste a meeting or interview transcript to generate a grounded article from it.
            The backend pipeline for this door is on the roadmap.
          </div>
        </div>
      ) : (
        // Name / LinkedIn door
        <div
          style={{
            padding: "24px",
            borderRadius: 14,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            boxShadow: "var(--shadow)",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {/* Primary input */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <label
                htmlFor="person-input"
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  fontFamily: "var(--font-mono), monospace",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--text3)",
                }}
              >
                Person
              </label>
              {inputTag && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    fontFamily: "var(--font-mono), monospace",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    padding: "2px 7px",
                    borderRadius: 5,
                    border: "1px solid color-mix(in srgb, var(--accent) 30%, transparent)",
                    background: "color-mix(in srgb, var(--accent) 10%, transparent)",
                    color: "var(--accent)",
                  }}
                >
                  {inputTag}
                </span>
              )}
            </div>
            <input
              id="person-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Sam Altman   or   https://linkedin.com/in/samaltman"
              disabled={disabled}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 9,
                border: "1px solid var(--border2)",
                background: "var(--inset)",
                color: "var(--text)",
                fontSize: 14,
                fontFamily: "inherit",
                outline: "none",
                boxSizing: "border-box",
                opacity: disabled ? 0.5 : 1,
              }}
            />
          </div>

          {/* Company */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label
              htmlFor="company-input"
              style={{
                fontSize: 10,
                fontWeight: 600,
                fontFamily: "var(--font-mono), monospace",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--text3)",
              }}
            >
              Company{" "}
              <span style={{ textTransform: "none", fontWeight: 400, letterSpacing: 0, color: "var(--text3)" }}>
                (optional — helps when names collide)
              </span>
            </label>
            <input
              id="company-input"
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="OpenAI"
              disabled={disabled}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 9,
                border: "1px solid var(--border2)",
                background: "var(--inset)",
                color: "var(--text)",
                fontSize: 14,
                fontFamily: "inherit",
                outline: "none",
                boxSizing: "border-box",
                opacity: disabled ? 0.5 : 1,
              }}
            />
          </div>

          {/* Evaluate toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              id="evaluate-toggle"
              type="checkbox"
              checked={evaluate}
              onChange={(e) => setEvaluate(e.target.checked)}
              disabled={disabled}
              style={{ cursor: "pointer", accentColor: "var(--accent)" }}
            />
            <label
              htmlFor="evaluate-toggle"
              style={{
                fontSize: 13,
                color: "var(--text2)",
                cursor: "pointer",
                userSelect: "none",
              }}
            >
              Run full evaluation{" "}
              <span style={{ color: "var(--text3)", fontSize: 12 }}>
                (LLM-judge evals — slower)
              </span>
            </label>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            variant="primary"
            disabled={!canSubmit}
            style={{ width: "100%", justifyContent: "center", padding: "12px 16px" }}
          >
            {disabled ? "Generating…" : "Generate article →"}
          </Button>
        </div>
      )}
    </form>
  );
}
