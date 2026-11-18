"use client";

import { Spinner } from "@/components/primitives/Spinner";
import { StatusDot } from "@/components/primitives/StatusDot";
import { formatDuration } from "@/lib/format";
import type { StageStatusToken } from "@/lib/status";
import type { StageOutput } from "@/lib/run-types";

export interface LiveStage {
  name: string;
  status: StageStatusToken;
  completedStage?: StageOutput;
}

interface ProcessingViewProps {
  subject: string;
  stages: LiveStage[];
  evaluating?: boolean;
}

const STAGE_LABEL: Record<string, string> = {
  ingest: "Ingest",
  enrich: "Enrich",
  research: "Research",
  draft: "Draft",
};

const STAGE_SUB: Record<string, string> = {
  ingest: "Normalise + validate input",
  enrich: "Resolve identity via Apollo",
  research: "Find sources + choose angle",
  draft: "Write + ground the article",
};

export function ProcessingView({ subject, stages, evaluating }: ProcessingViewProps) {
  const doneCount = stages.filter((s) => s.status === "ok" || s.status === "error").length;
  const total = stages.length;
  const progress = total > 0 ? doneCount / total : 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeIn 0.25s ease",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Spinner size={18} />
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>
            Generating article
          </div>
          <div style={{ fontSize: 13, color: "var(--text3)" }}>
            {subject}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div
        style={{
          height: 4,
          borderRadius: 999,
          background: "var(--surface2)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 999,
            background: "var(--accent)",
            width: `${progress * 100}%`,
            transition: "width 0.5s ease",
          }}
        />
      </div>

      {/* Stage list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {stages.map((stage) => {
          const label = STAGE_LABEL[stage.name] ?? stage.name;
          const sub = STAGE_SUB[stage.name] ?? "";
          const duration = stage.completedStage?.duration_ms;

          return (
            <div
              key={stage.name}
              style={{
                display: "grid",
                gridTemplateColumns: "16px 1fr auto",
                alignItems: "center",
                gap: 12,
                padding: "10px 14px",
                borderRadius: 10,
                border: `1px solid ${
                  stage.status === "running"
                    ? "color-mix(in srgb, var(--run) 35%, var(--border))"
                    : "var(--border)"
                }`,
                background:
                  stage.status === "running"
                    ? "color-mix(in srgb, var(--run) 5%, var(--surface))"
                    : "var(--surface)",
                transition: "border-color 0.25s, background 0.25s",
              }}
            >
              {stage.status === "pending" ? (
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: "var(--border2)",
                    display: "inline-block",
                    margin: "auto",
                  }}
                />
              ) : (
                <StatusDot status={stage.status} size={7} />
              )}

              <div style={{ overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color:
                      stage.status === "pending" ? "var(--text3)" : "var(--text)",
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--text3)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {sub}
                </div>
              </div>

              <div
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono), monospace",
                  color: "var(--text3)",
                  whiteSpace: "nowrap",
                }}
              >
                {stage.status === "running" && (
                  <Spinner size={11} color="var(--run)" />
                )}
                {duration !== undefined && stage.status !== "running" && (
                  formatDuration(duration)
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Evaluating */}
      {evaluating && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "10px 14px",
            borderRadius: 10,
            border: "1px solid color-mix(in srgb, var(--accent) 30%, var(--border))",
            background: "color-mix(in srgb, var(--accent) 6%, var(--surface))",
          }}
        >
          <Spinner size={12} color="var(--accent)" />
          <span style={{ fontSize: 13, color: "var(--text2)" }}>
            Running LLM-judge evaluations…
          </span>
        </div>
      )}
    </div>
  );
}
