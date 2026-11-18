"use client";

import { useState } from "react";
import { StatusPill } from "@/components/primitives/StatusPill";
import { EvalPill } from "@/components/primitives/EvalPill";
import { CodeWell } from "@/components/primitives/CodeWell";
import { EvalCard } from "./EvalCard";
import { stagePill } from "@/lib/eval-mapping";
import { formatDuration } from "@/lib/format";
import type { EvalReport, StageOutput } from "@/lib/run-types";

interface StageItemProps {
  stage: StageOutput;
  index: number;
  evals: EvalReport | null;
}

const STAGE_SUB: Record<string, string> = {
  ingest: "Normalise + validate input",
  enrich: "Resolve identity via Apollo",
  research: "Find sources + choose angle",
  draft: "Write + ground the article",
};

const STAGE_LABEL: Record<string, string> = {
  ingest: "Ingest",
  enrich: "Enrich",
  research: "Research",
  draft: "Draft",
};

export function StageItem({ stage, index, evals }: StageItemProps) {
  const [open, setOpen] = useState(false);
  const evalPillVerdict = stagePill(evals, stage.name);
  const verdict = evals?.verdicts.find(
    (v) => {
      const map: Record<string, string> = {
        enrich: "entity_resolution",
        research: "angle_support",
        draft: "groundedness",
      };
      return v.name === map[stage.name];
    }
  );

  const stageStatus = stage.status === "ok" ? "ok" : "error";
  const label = STAGE_LABEL[stage.name] ?? stage.name;
  const sub = STAGE_SUB[stage.name] ?? "";

  return (
    <div
      style={{
        borderRadius: 12,
        border: `1px solid ${open ? "var(--border2)" : "var(--border)"}`,
        background: "var(--surface)",
        overflow: "hidden",
        boxShadow: open ? "var(--shadow)" : "none",
        transition: "border-color 0.15s",
      }}
    >
      {/* Header row */}
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "grid",
          gridTemplateColumns: "28px 1fr auto auto auto",
          alignItems: "center",
          gap: 12,
          padding: "12px 16px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            fontFamily: "var(--font-mono), monospace",
            color: "var(--text3)",
          }}
        >
          {String(index + 1).padStart(2, "0")}
        </span>

        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
            {label}
          </div>
          <div
            style={{
              fontSize: 11,
              color: "var(--text3)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {sub}
          </div>
        </div>

        <StatusPill status={stageStatus} />

        {evalPillVerdict && <EvalPill verdict={evalPillVerdict} mini />}

        <span
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono), monospace",
            color: "var(--text3)",
          }}
        >
          {formatDuration(stage.duration_ms)}
        </span>

        <span
          style={{
            fontSize: 12,
            color: "var(--text3)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 0.15s",
          }}
        >
          ▾
        </span>
      </button>

      {/* Expanded body */}
      {open && (
        <div
          style={{
            padding: "0 16px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            borderTop: "1px solid var(--border)",
            paddingTop: 14,
          }}
        >
          {/* Input / Output wells */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <CodeWell label="Input" value={stage.output === null ? "—" : undefined} />
            <CodeWell label="Output" value={stage.output} />
          </div>

          {/* Error detail */}
          {stage.error && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 9,
                border: "1px solid color-mix(in srgb, var(--fail) 26%, transparent)",
                background: "color-mix(in srgb, var(--fail) 8%, transparent)",
                fontSize: 13,
                color: "var(--fail)",
                fontFamily: "var(--font-mono), monospace",
              }}
            >
              {stage.error.code}: {stage.error.message}
            </div>
          )}

          {/* Eval card */}
          {verdict && <EvalCard verdict={verdict} />}
        </div>
      )}
    </div>
  );
}
