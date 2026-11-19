"use client";

import { useState } from "react";
import { Button } from "@/components/primitives/Button";
import { CodeWell } from "@/components/primitives/CodeWell";
import { formatDuration } from "@/lib/format";
import type { RunDetail, StageName } from "@/lib/types";
import { STAGE_WORDS } from "./LiveStages";

const STATUS_COLOR: Record<string, string> = {
  completed: "var(--pass)",
  failed: "var(--fail)",
  running: "var(--run)",
};

/** Each stage's record: what it was given, what it produced, what it cost. */
export function Trace({
  run,
  openStage,
  busy,
  onReplay,
}: {
  run: RunDetail;
  openStage: StageName | null;
  busy: boolean;
  onReplay: (from: StageName) => void;
}) {
  const [open, setOpen] = useState<StageName | null>(openStage);
  return (
    <section className="panel">
      <h2 className="micro" style={{ margin: "0 0 10px" }}>
        The trace · every stage, with what went in and what came out
      </h2>
      <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
        {run.stages.map((stage, position) => {
          const call = run.model_calls.find((c) => c.stage === stage.name);
          const expanded = open === stage.name;
          return (
            <li key={stage.name} style={{ border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface2)" }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, padding: "10px 12px" }}>
                <span className="micro" style={{ width: 14 }}>{position + 1}</span>
                <span style={{ flex: "1 1 220px", minWidth: 0 }}>
                  <span style={{ fontWeight: 600 }}>{stage.name}</span>
                  <span style={{ color: "var(--text2)", marginLeft: 8, fontSize: 13 }}>{STAGE_WORDS[stage.name]}</span>
                </span>
                <span style={{ fontFamily: "var(--font-mono), monospace", fontSize: 12, color: STATUS_COLOR[stage.status] ?? "var(--text2)" }}>
                  {stage.status}
                  {stage.error ? ` (${stage.error})` : ""}
                  {stage.duration_ms != null ? ` · ${formatDuration(stage.duration_ms)}` : ""}
                </span>
                <Button variant="ghost" onClick={() => setOpen(expanded ? null : stage.name)} aria-expanded={expanded}>
                  {expanded ? "Hide" : "Show"} input and output
                </Button>
                <Button variant="secondary" disabled={busy} onClick={() => onReplay(stage.name)}>
                  Re-run from here
                </Button>
              </div>
              {(stage.copied_from_run_id || call) && (
                <div style={{ padding: "0 12px 10px 36px", fontSize: 12.5, color: "var(--text3)", lineHeight: 1.6 }}>
                  {stage.copied_from_run_id && <div>Copied from run {stage.copied_from_run_id}; not run again.</div>}
                  {call && (
                    <div>
                      Model {call.model_requested}
                      {call.input_tokens != null ? ` · ${call.input_tokens} tokens in, ${call.output_tokens} out` : ""}
                      {call.latency_ms != null ? ` · ${formatDuration(call.latency_ms)} when recorded` : ""}
                      {` · $${call.cost_usd.toFixed(4)}`}
                      {call.source === "fixture" ? " when recorded; replayed now at no cost" : ""}
                      {call.error ? ` · failed: ${call.error}` : ""}
                    </div>
                  )}
                </div>
              )}
              {expanded && (
                <div style={{ padding: "0 12px 12px", display: "grid", gap: 10 }}>
                  <CodeWell label="Input" value={stage.input} maxHeight={260} />
                  <CodeWell label="Output" value={stage.output} maxHeight={320} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
