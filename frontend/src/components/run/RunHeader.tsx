"use client";

import { useState } from "react";
import { Chip } from "@/components/primitives/Chip";
import { Button } from "@/components/primitives/Button";
import { StatusPill } from "@/components/primitives/StatusPill";
import { EvalCard } from "./EvalCard";
import { getRunSummary, getRunLevelVerdict } from "@/lib/eval-mapping";
import { formatDuration } from "@/lib/format";
import type { Run } from "@/lib/run-types";

interface RunHeaderProps {
  run: Run;
  onRunEvals?: () => void;
  evalsLoading?: boolean;
}

export function RunHeader({ run, onRunEvals, evalsLoading }: RunHeaderProps) {
  const [showRunLevelEval, setShowRunLevelEval] = useState(false);
  const summary = getRunSummary(run);
  const runLevelVerdict = getRunLevelVerdict(run.evals);

  const subjectLabel = [
    run.input.name,
    run.input.company,
    run.input.linkedin_url?.split("/in/")[1]?.replace(/-/g, " "),
  ]
    .filter(Boolean)
    .join(" · ");

  const status = run.status === "completed" ? "ok" : run.status === "failed" ? "error" : "pending";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Title row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--accent)",
              marginBottom: 6,
            }}
          >
            Article run · {run.id.slice(0, 8)}
          </div>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 600,
              color: "var(--text)",
              letterSpacing: "-0.01em",
              lineHeight: 1.3,
              margin: 0,
            }}
          >
            {run.article?.title ?? subjectLabel}
          </h1>
          {run.article?.title && (
            <p style={{ fontSize: 13, color: "var(--text3)", margin: "4px 0 0" }}>
              {subjectLabel}
            </p>
          )}
        </div>
        <StatusPill status={status} />
      </div>

      {/* Summary chips */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <Chip label="stages" value={summary.stageCount} />
        <Chip label="duration" value={formatDuration(summary.totalDurationMs)} />
        {summary.evalsPassCount !== null ? (
          <Chip
            label="evals"
            value={`${summary.evalsPassCount}/${summary.evalsTotalCount}`}
            valueColor={
              summary.evalsPassCount === summary.evalsTotalCount
                ? "var(--pass)"
                : "var(--err)"
            }
          />
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Chip label="evals" value="—" />
            {onRunEvals && (
              <Button
                variant="ghost"
                onClick={onRunEvals}
                disabled={evalsLoading}
                style={{ fontSize: 12, padding: "4px 10px" }}
              >
                {evalsLoading ? "Evaluating…" : "Run evals"}
              </Button>
            )}
          </div>
        )}
        {summary.overallScore !== null && (
          <Chip
            label="score"
            value={(summary.overallScore * 100).toFixed(0) + "%"}
            valueColor={
              summary.overallScore >= 0.8
                ? "var(--pass)"
                : summary.overallScore >= 0.5
                ? "var(--err)"
                : "var(--fail)"
            }
          />
        )}
      </div>

      {/* Run-level eval (stage_validity) */}
      {runLevelVerdict && (
        <div>
          <button
            onClick={() => setShowRunLevelEval((v) => !v)}
            style={{
              background: "none",
              border: "none",
              color: "var(--text3)",
              fontSize: 12,
              cursor: "pointer",
              fontFamily: "var(--font-mono), monospace",
              padding: 0,
              marginBottom: showRunLevelEval ? 8 : 0,
            }}
          >
            {showRunLevelEval ? "▼" : "▶"} stage validity
          </button>
          {showRunLevelEval && <EvalCard verdict={runLevelVerdict} />}
        </div>
      )}
    </div>
  );
}
