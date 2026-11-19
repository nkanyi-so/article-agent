/** Folds a run's events into the state of its five stages. Pure, so it is tested. */

import type { AnyEvent } from "./stream";
import { STAGES, type StageName } from "./types";

export type StageState = {
  name: StageName;
  status: "waiting" | "running" | "done" | "copied" | "failed";
  durationMs?: number;
};

export type LiveRun = {
  runId: string | null;
  stages: StageState[];
  /** Null while the run is going; then how it ended. */
  ended: null | { ok: true } | { ok: false; error: string };
};

export function startLiveRun(): LiveRun {
  return { runId: null, stages: STAGES.map((name) => ({ name, status: "waiting" })), ended: null };
}

function withStage(run: LiveRun, name: string, change: Partial<StageState>): StageState[] {
  return run.stages.map((stage) => (stage.name === name ? { ...stage, ...change } : stage));
}

export function applyEvent(run: LiveRun, event: AnyEvent): LiveRun {
  switch (event.type) {
    case "run_started":
      return { ...run, runId: event.run_id };
    case "stage_started":
      return { ...run, stages: withStage(run, event.stage, { status: "running" }) };
    case "stage_completed":
      return {
        ...run,
        stages: withStage(run, event.stage, {
          status: event.copied_from_run_id ? "copied" : "done",
          durationMs: event.duration_ms,
        }),
      };
    case "run_completed":
      return { ...run, ended: { ok: true } };
    case "run_failed":
      return {
        ...run,
        stages: run.stages.map((stage) =>
          stage.status === "running" ? { ...stage, status: "failed" } : stage
        ),
        ended: { ok: false, error: event.error },
      };
    case "stream_ended_early":
      return {
        ...run,
        runId: run.runId ?? event.run_id,
        stages: run.stages.map((stage) =>
          stage.status === "running" ? { ...stage, status: "failed" } : stage
        ),
        ended: { ok: false, error: "stream_ended_early" },
      };
  }
}
