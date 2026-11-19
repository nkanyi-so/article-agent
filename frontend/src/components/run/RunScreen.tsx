"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError, messageFor } from "@/lib/api";
import { replayedFromRecordings } from "@/lib/article";
import { DEMO_LINE, linkMayStartRuns } from "@/lib/copy";
import { formatDate } from "@/lib/format";
import { applyEvent, startLiveRun, type LiveRun } from "@/lib/live";
import { STAGES, type RunDetail, type StageName } from "@/lib/types";
import { ArticlePanel, EvidencePanel, FlagList, RemovedList, ScoreCards, type Selection } from "./ArticleParts";
import { LiveStages } from "./LiveStages";
import { Trace } from "./Trace";

/** What the address asks to be shown: `?claim=3`, `?claim=headline`, `?stage=draft`. */
function fromAddress(): { selected: Selection; stage: StageName | null; rerun: StageName | null } {
  if (typeof window === "undefined") return { selected: null, stage: null, rerun: null };
  const query = new URLSearchParams(window.location.search);
  const claim = query.get("claim");
  const stage = query.get("stage");
  const selected: Selection =
    claim === "headline" ? "headline" : claim !== null && /^\d+$/.test(claim) ? Number(claim) : null;
  const named = (value: string | null): StageName | null =>
    STAGES.includes(value as StageName) ? (value as StageName) : null;
  return { selected, stage: named(stage), rerun: named(query.get("rerun")) };
}

export function RunScreen({ run }: { run: RunDetail }) {
  const router = useRouter();
  const [initial] = useState(fromAddress);
  const [selected, setSelected] = useState<Selection>(
    typeof initial.selected === "number" && initial.selected >= (run.article?.claims.length ?? 0)
      ? null
      : initial.selected
  );
  const [replay, setReplay] = useState<{ from: StageName; live: LiveRun } | null>(null);
  const [replayError, setReplayError] = useState<string | null>(null);

  // The address follows the chosen sentence, so a view of one sentence can be shared.
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (selected === null) query.delete("claim");
    else query.set("claim", String(selected));
    const text = query.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${text ? `?${text}` : ""}`);
  }, [selected]);

  const startReplay = useCallback(
    (from: StageName) => {
      let live = startLiveRun();
      setReplayError(null);
      setReplay({ from, live });
      api
        .replay(run.run.id, from, (event) => {
          live = applyEvent(live, event);
          setReplay({ from, live });
          // The new run exists and has ended, whichever way: go and look at it.
          if (live.ended && live.runId) router.push(`/runs/${live.runId}`);
          else if (live.ended && !live.ended.ok) setReplayError(messageFor(live.ended.error));
        })
        .catch((error: unknown) => {
          setReplay(null);
          setReplayError(messageFor(error instanceof ApiError ? error.code : null));
        });
    },
    [router, run.run.id]
  );

  // `?rerun=draft` starts a re-run on arrival, but only when the server says it replays
  // recordings: a link must never be able to start a paid run.
  useEffect(() => {
    const from = initial.rerun;
    if (!from) return;
    let stale = false;
    api
      .config()
      .then((config) => {
        if (!stale && linkMayStartRuns(config)) startReplay(from);
      })
      .catch(() => undefined);
    return () => {
      stale = true;
    };
  }, [initial.rerun, startReplay]);

  const { article } = run;
  const replayed = replayedFromRecordings(run);
  const busy = replay !== null && replay.live.ended === null;

  return (
    <div className="page" style={{ display: "grid", gap: 20 }}>
      <header>
        <div className="micro" style={{ color: "var(--accent)", marginBottom: 8 }}>
          Run {run.run.id} · {run.run.status}
          {run.run.created_at ? ` · ${formatDate(run.run.created_at)}` : ""}
        </div>
        <div style={{ fontSize: 13, color: "var(--text2)", lineHeight: 1.6 }}>
          From the transcript “{run.run.title}”.{" "}
          {run.run.parent_run_id && (
            <>
              Re-run of{" "}
              <Link className="link" href={`/runs/${run.run.parent_run_id}`}>
                {run.run.parent_run_id}
              </Link>{" "}
              from the {run.run.replay_from_stage} stage.{" "}
            </>
          )}
        </div>
        {replayed && (
          <p className="demo-line" style={{ margin: "12px 0 0" }}>
            {DEMO_LINE} The recorded calls for this run cost ${run.cost_usd.toFixed(4)}.
          </p>
        )}
      </header>

      {replay && (
        <section className="panel" aria-label="Re-run in progress">
          <h2 className="micro" style={{ margin: "0 0 10px" }}>
            Re-running from the {replay.from} stage · earlier stages are copied, the rest run again
          </h2>
          <LiveStages stages={replay.live.stages} />
        </section>
      )}
      {replayError && (
        <div className="note-removed" role="alert">
          {replayError}
        </div>
      )}

      {run.run.status === "failed" && (
        <div className="note-removed" role="alert">
          <div className="micro" style={{ color: "var(--fail)", marginBottom: 4 }}>This run failed</div>
          {messageFor(run.run.error)}
          {article ? " What the draft contained before it was refused is shown below." : ""}
        </div>
      )}

      {article && (
        <>
          <ScoreCards run={run} />
          <div className="run-grid">
            <ArticlePanel run={run} selected={selected} onSelect={setSelected} />
            <EvidencePanel run={run} selected={selected} onClose={() => setSelected(null)} />
          </div>
          <FlagList run={run} onSelect={setSelected} />
          <RemovedList run={run} />
        </>
      )}

      <Trace run={run} openStage={initial.stage} busy={busy} onReplay={startReplay} />
    </div>
  );
}
