/** The entry: pick one of the seeded transcripts, watch the stages arrive, read the result. */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/primitives/Button";
import { LiveStages } from "@/components/run/LiveStages";
import { api, ApiError, messageFor } from "@/lib/api";
import { CLAIM, DEMO_LINE, linkMayStartRuns } from "@/lib/copy";
import { applyEvent, startLiveRun, type LiveRun } from "@/lib/live";
import { myRuns, rememberRun, type MyRun } from "@/lib/my-runs";
import type { ConfigResponse } from "@/lib/types";

type Loaded = { state: "loading" } | { state: "ready"; config: ConfigResponse } | { state: "error"; code: string };

export default function EntryPage() {
  const router = useRouter();
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading" });
  const [running, setRunning] = useState<{ title: string; live: LiveRun } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState("");
  const [title, setTitle] = useState("");
  const [mine, setMine] = useState<MyRun[]>([]);

  // Read after the page is in the browser: the list lives in the browser's own storage.
  useEffect(() => {
    const timer = window.setTimeout(() => setMine(myRuns()), 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    let stale = false;
    api
      .config()
      .then((config) => {
        if (!stale) setLoaded({ state: "ready", config });
      })
      .catch((caught: unknown) => {
        if (!stale) setLoaded({ state: "error", code: caught instanceof ApiError ? caught.code : "internal_error" });
      });
    return () => {
      stale = true;
    };
  }, []);

  function follow(runTitle: string, start: (onEvent: Parameters<typeof api.startSeed>[1]) => Promise<void>) {
    let live = startLiveRun();
    setError(null);
    setRunning({ title: runTitle, live });
    start((event) => {
      live = applyEvent(live, event);
      setRunning({ title: runTitle, live });
      if (!live.ended) return;
      // The address changes only now, when the run exists and has ended. A failed run has
      // a page too: it shows what failed and what was stored.
      if (live.runId) {
        if (live.ended.ok) {
          rememberRun({ id: live.runId, title: runTitle, kind: "run", at: new Date().toISOString() });
        }
        router.push(`/runs/${live.runId}`);
      } else {
        setRunning(null);
        setError(messageFor(live.ended.ok ? null : live.ended.error));
      }
    }).catch((caught: unknown) => {
      // Refused before any run was created: say why, and stay here.
      setRunning(null);
      setError(messageFor(caught instanceof ApiError ? caught.code : null));
    });
  }

  // `?start=<seed>` starts that transcript on arrival, in demo mode only: a link must
  // never be able to start a paid run.
  const demo = loaded.state === "ready" && linkMayStartRuns(loaded.config) ? loaded.config : null;
  useEffect(() => {
    if (!demo) return;
    const wanted = new URLSearchParams(window.location.search).get("start");
    const seed = demo.seeds.find((candidate) => candidate.id === wanted);
    if (!seed) return;
    const timer = window.setTimeout(
      () => follow(seed.title, (onEvent) => api.startSeed(seed.id, onEvent)),
      0
    );
    return () => window.clearTimeout(timer);
    // Runs once, when the configuration arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  if (running) {
    return (
      <div className="page" style={{ maxWidth: 760, display: "grid", gap: 16 }}>
        <div>
          <div className="micro" style={{ color: "var(--accent)", marginBottom: 8 }}>Running</div>
          <h1 style={{ fontSize: 22, margin: 0, letterSpacing: "-0.01em" }}>{running.title}</h1>
        </div>
        <LiveStages stages={running.live.stages} />
        <p style={{ margin: 0, color: "var(--text3)", fontSize: 13 }}>
          The stages arrive over a live stream. The article opens when the last one ends.
        </p>
      </div>
    );
  }

  const config = loaded.state === "ready" ? loaded.config : null;
  const pasteEnabled = config?.paste_enabled ?? false;

  return (
    <div className="page" style={{ maxWidth: 920, display: "grid", gap: 22 }}>
      <header>
        <div className="micro" style={{ color: "var(--accent)", marginBottom: 10 }}>
          Transcript in, checked article out
        </div>
        <h1 style={{ fontSize: 26, lineHeight: 1.25, letterSpacing: "-0.02em", margin: "0 0 10px" }}>
          An article you can check against what was said
        </h1>
        <p style={{ fontSize: 15, color: "var(--text2)", lineHeight: 1.65, margin: 0, maxWidth: 720 }}>{CLAIM}</p>
      </header>

      {(!config || config.mode === "demo") && <p className="demo-line" style={{ margin: 0 }}>{DEMO_LINE}</p>}

      {error && (
        <div className="note-removed" role="alert">
          {error}
        </div>
      )}
      {loaded.state === "error" && (
        <div className="note-removed" role="alert">
          {messageFor(loaded.code)}
        </div>
      )}

      <section>
        <h2 className="micro" style={{ margin: "0 0 10px" }}>Transcripts of fictional meetings</h2>
        <div className="seed-row">
          {(config?.seeds ?? []).map((seed) => (
            <div key={seed.id} className="panel" style={{ display: "grid", gap: 12, alignContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 600, lineHeight: 1.4 }}>{seed.title}</div>
                {seed.note && (
                  <div className="note-flag" style={{ marginTop: 8, fontSize: 12.5, lineHeight: 1.5 }}>
                    {seed.note}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                <Link href={`/runs/seed-${seed.id}`} style={{ textDecoration: "none" }}>
                  <Button variant="primary" tabIndex={-1}>Read the checked article</Button>
                </Link>
                <Button variant="secondary" onClick={() => follow(seed.title, (onEvent) => api.startSeed(seed.id, onEvent))}>
                  Run it now
                </Button>
              </div>
            </div>
          ))}
          {loaded.state === "loading" && <div style={{ color: "var(--text3)" }}>Loading the transcripts…</div>}
        </div>
      </section>

      {mine.length > 0 && (
        <section aria-label="Runs you started">
          <h2 className="micro" style={{ margin: "0 0 10px" }}>Runs you started in this browser</h2>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
            {mine.map((run) => (
              <li key={run.id}>
                <Link className="link" href={`/runs/${run.id}`}>
                  {run.title.split(":")[0]} · {run.kind}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="panel">
        <h2 className="micro" style={{ margin: "0 0 10px" }}>Or paste a transcript</h2>
        <p style={{ margin: "0 0 10px", color: "var(--text2)", fontSize: 13, lineHeight: 1.6 }}>
          {pasteEnabled
            ? "One turn per line, each starting with the speaker's name and a colon. This calls the models and costs a few cents."
            : "Not available here: this demo replays recordings and has no key, so it cannot write about a new transcript. Running the project locally with your own key enables this box."}
        </p>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          disabled={!pasteEnabled}
          placeholder="Title, for example: Harbour committee, March meeting"
          aria-label="Title"
          style={{ width: "100%", padding: "8px 10px", marginBottom: 8, borderRadius: 6, border: "1px solid var(--border2)", background: "var(--inset)", color: "var(--text)" }}
        />
        <textarea
          value={transcript}
          onChange={(event) => setTranscript(event.target.value)}
          disabled={!pasteEnabled}
          rows={5}
          placeholder={"Ana Ruiz: We open the second depot in May.\nLeo Brandt: The budget for it was approved last week."}
          aria-label="Transcript"
          style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid var(--border2)", background: "var(--inset)", color: "var(--text)", fontFamily: "var(--font-mono), monospace", fontSize: 12.5, opacity: pasteEnabled ? 1 : 0.6 }}
        />
        <div style={{ marginTop: 10 }}>
          <Button
            variant="primary"
            disabled={!pasteEnabled || !transcript.trim() || !title.trim()}
            onClick={() => follow(title, (onEvent) => api.startPaste(transcript, title, onEvent))}
          >
            Write the article
          </Button>
        </div>
      </section>
    </div>
  );
}
