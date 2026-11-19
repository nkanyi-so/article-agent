import { Spinner } from "@/components/primitives/Spinner";
import { formatDuration } from "@/lib/format";
import type { StageState } from "@/lib/live";
import type { StageName } from "@/lib/types";

export type LiveStage = StageState;

export const STAGE_WORDS: Record<StageName, string> = {
  ingest: "Split the transcript into numbered lines (code)",
  extract: "List what was said (model)",
  draft: "Write the article, citing lines (model)",
  ground: "Remove sentences the cited lines do not back (code)",
  evaluate: "Check the records, then ask a judge model (code, then model)",
};

const COLOR: Record<LiveStage["status"], string> = {
  waiting: "var(--text3)",
  running: "var(--run)",
  done: "var(--pass)",
  copied: "var(--text2)",
  failed: "var(--fail)",
};

const WORD: Record<LiveStage["status"], string> = {
  waiting: "waiting",
  running: "running",
  done: "done",
  copied: "copied from the earlier run",
  failed: "failed",
};

/** The five stages as they arrive from the event stream. */
export function LiveStages({ stages }: { stages: LiveStage[] }) {
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }} aria-live="polite">
      {stages.map((stage, position) => (
        <li
          key={stage.name}
          className="panel"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 14px",
            opacity: stage.status === "waiting" ? 0.55 : 1,
          }}
        >
          <span className="micro" style={{ width: 18 }}>
            {position + 1}
          </span>
          <span style={{ flex: 1, minWidth: 0 }}>
            <span style={{ fontWeight: 600 }}>{stage.name}</span>
            <span style={{ color: "var(--text2)", marginLeft: 8, fontSize: 13 }}>
              {STAGE_WORDS[stage.name]}
            </span>
          </span>
          {stage.status === "running" && <Spinner size={14} />}
          <span style={{ color: COLOR[stage.status], fontSize: 12, fontFamily: "var(--font-mono), monospace" }}>
            {WORD[stage.status]}
            {stage.durationMs !== undefined && stage.status !== "copied"
              ? ` · ${formatDuration(stage.durationMs)}`
              : ""}
          </span>
        </li>
      ))}
    </ol>
  );
}
