"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { InputForm } from "@/components/new-article/InputForm";
import { DisambiguationChooser } from "@/components/new-article/DisambiguationChooser";
import { RunErrorNotice } from "@/components/new-article/RunErrorNotice";
import { ProcessingView, type LiveStage } from "@/components/run/ProcessingView";
import { api, ApiError } from "@/lib/api";
import type { EnrichCandidate, FormRequest, Run } from "@/lib/run-types";
import type { StageStatusToken } from "@/lib/status";

const ALL_STAGES = ["ingest", "enrich", "research", "draft"];

function initStages(): LiveStage[] {
  return ALL_STAGES.map((name) => ({ name, status: "pending" as StageStatusToken }));
}

type PageState =
  | { phase: "idle" }
  | { phase: "streaming"; subject: string; stages: LiveStage[]; evaluating: boolean }
  | { phase: "disambiguation"; candidates: EnrichCandidate[]; runId: string }
  | { phase: "error"; error: ApiError | Error; partialRun?: Run };

export default function HomePage() {
  const router = useRouter();
  const [state, setState] = useState<PageState>({ phase: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  const startRun = useCallback((form: FormRequest, evaluate: boolean) => {
    // Cancel any existing stream.
    abortRef.current?.abort();

    const subject =
      form.name ??
      form.linkedin_url?.split("/in/")[1]?.replace(/-/g, " ") ??
      "Unknown";

    setState({
      phase: "streaming",
      subject,
      stages: initStages(),
      evaluating: false,
    });

    const controller = api.streamRun(form, evaluate, {
      onRunStarted: (data) => {
        // Silently update the URL to be the canonical run URL so it's shareable,
        // without remounting (we stay on this client component to keep the stream alive).
        window.history.replaceState(null, "", `/runs/${data.run_id}`);
      },

      onStageStarted: ({ name }) => {
        setState((prev) => {
          if (prev.phase !== "streaming") return prev;
          return {
            ...prev,
            stages: prev.stages.map((s) =>
              s.name === name ? { ...s, status: "running" } : s
            ),
          };
        });
      },

      onStageCompleted: ({ stage }) => {
        setState((prev) => {
          if (prev.phase !== "streaming") return prev;
          return {
            ...prev,
            stages: prev.stages.map((s) =>
              s.name === stage.name
                ? {
                    ...s,
                    status: stage.status === "ok" ? "ok" : "error",
                    completedStage: stage,
                  }
                : s
            ),
          };
        });
      },

      onNeedsDisambiguation: ({ candidates, run_id }) => {
        setState({ phase: "disambiguation", candidates, runId: run_id });
      },

      onEvaluating: () => {
        setState((prev) => {
          if (prev.phase !== "streaming") return prev;
          return { ...prev, evaluating: true };
        });
      },

      onCompleted: ({ run }) => {
        // Navigate to the canonical run view (pipeline tab).
        router.push(`/runs/${run.id}`);
      },

      onFailed: ({ run }) => {
        const err = run.error
          ? new ApiError(
              run.error.http_status,
              run.error.message,
              run.error.code,
              run.error.retryable,
            )
          : new ApiError(500, "Pipeline failed");
        setState({ phase: "error", error: err, partialRun: run });
      },

      onError: (err) => {
        setState({ phase: "error", error: err });
      },
    });

    abortRef.current = controller;
  }, [router]);

  function handleDisambiguationPick(form: FormRequest) {
    startRun(form, false);
  }

  function reset() {
    abortRef.current?.abort();
    setState({ phase: "idle" });
    // Push back to "/" to restore the form URL.
    window.history.replaceState(null, "", "/");
  }

  return (
    <div
      style={{
        maxWidth: 640,
        margin: "0 auto",
        padding: "48px 24px 80px",
        width: "100%",
      }}
    >
      {/* Hero header — visible only when idle */}
      {state.phase === "idle" && (
        <div style={{ marginBottom: 32 }}>
          <div
            style={{
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono), monospace",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--accent)",
              marginBottom: 12,
            }}
          >
            New article
          </div>
          <h1
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: "var(--text)",
              marginBottom: 8,
              letterSpacing: "-0.02em",
              lineHeight: 1.25,
            }}
          >
            Start from a name or profile
          </h1>
          <p style={{ fontSize: 14, color: "var(--text2)", lineHeight: 1.6, margin: 0 }}>
            Bylined researches the person, picks a grounded angle, writes a draft,
            and traces every claim back to a real source.
          </p>
        </div>
      )}

      {/* Main content area */}
      {state.phase === "idle" && (
        <InputForm onSubmit={startRun} />
      )}

      {state.phase === "streaming" && (
        <ProcessingView
          subject={state.subject}
          stages={state.stages}
          evaluating={state.evaluating}
        />
      )}

      {state.phase === "disambiguation" && (
        <DisambiguationChooser
          candidates={state.candidates}
          onPick={handleDisambiguationPick}
          onCancel={reset}
        />
      )}

      {state.phase === "error" && (
        <RunErrorNotice
          error={state.error}
          partialRun={state.partialRun}
          onRetry={reset}
        />
      )}
    </div>
  );
}
