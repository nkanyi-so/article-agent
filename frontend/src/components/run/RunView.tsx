"use client";

import { useState } from "react";
import { SegmentedControl } from "@/components/primitives/SegmentedControl";
import { RunHeader } from "./RunHeader";
import { ArticleView } from "./ArticleView";
import { StageItem } from "./StageItem";
import { api } from "@/lib/api";
import type { Run } from "@/lib/run-types";

interface RunViewProps {
  run: Run;
  onRunUpdated?: (run: Run) => void;
}

type RunTab = "article" | "trace";

export function RunView({ run: initialRun, onRunUpdated }: RunViewProps) {
  const [run, setRun] = useState<Run>(initialRun);
  const [tab, setTab] = useState<RunTab>("article");
  const [evalsLoading, setEvalsLoading] = useState(false);

  async function handleRunEvals() {
    setEvalsLoading(true);
    try {
      const updated = await api.runEvals(run.id);
      setRun(updated);
      onRunUpdated?.(updated);
    } catch (err) {
      console.error("Failed to run evals:", err);
    } finally {
      setEvalsLoading(false);
    }
  }

  const stages = [run.ingest, run.enrich, run.research, run.draft].filter(
    (s): s is NonNullable<typeof s> => s !== null && s !== undefined
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        animation: "fadeIn 0.3s ease",
      }}
    >
      <RunHeader
        run={run}
        onRunEvals={run.evals ? undefined : handleRunEvals}
        evalsLoading={evalsLoading}
      />

      {/* Article/Trace toggle (only if run completed with an article) */}
      {run.article && (
        <div>
          <SegmentedControl
            options={[
              { value: "article" as RunTab, label: "Article" },
              { value: "trace" as RunTab, label: "Trace" },
            ]}
            value={tab}
            onChange={setTab}
          />
        </div>
      )}

      {/* Article view */}
      {tab === "article" && run.article && <ArticleView run={run} />}

      {/* Trace view — stage inspector */}
      {(tab === "trace" || !run.article) && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stages.length === 0 ? (
            <div style={{ color: "var(--text3)", fontSize: 13 }}>
              No stage data available.
            </div>
          ) : (
            stages.map((stage, i) => (
              <StageItem
                key={stage.name}
                stage={stage}
                index={i}
                evals={run.evals}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
