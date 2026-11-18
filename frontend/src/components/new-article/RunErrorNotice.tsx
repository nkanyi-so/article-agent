"use client";

import { Button } from "@/components/primitives/Button";
import type { ApiError } from "@/lib/api";
import type { Run } from "@/lib/run-types";

interface RunErrorNoticeProps {
  error: ApiError | Error;
  partialRun?: Run | null;
  onRetry: () => void;
}

export function RunErrorNotice({ error, partialRun, onRetry }: RunErrorNoticeProps) {
  const isApiError = "code" in error && error.code !== undefined;
  const code = isApiError ? (error as ApiError).code : null;
  const retryable = isApiError ? (error as ApiError).retryable : false;

  return (
    <div
      style={{
        padding: 24,
        borderRadius: 14,
        border: "1px solid color-mix(in srgb, var(--fail) 26%, transparent)",
        background: "color-mix(in srgb, var(--fail) 8%, transparent)",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div>
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            fontFamily: "var(--font-mono), monospace",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--fail)",
            marginBottom: 6,
          }}
        >
          Pipeline failed
          {code && (
            <span style={{ marginLeft: 8, opacity: 0.7 }}>· {code}</span>
          )}
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
          {error.message}
        </div>
        {retryable && (
          <div style={{ fontSize: 13, color: "var(--text3)", marginTop: 4 }}>
            This error may resolve on retry.
          </div>
        )}
      </div>

      {/* Show partial trace if we have a failed run */}
      {partialRun && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 9,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            fontSize: 12,
            fontFamily: "var(--font-mono), monospace",
            color: "var(--text3)",
            lineHeight: 1.7,
          }}
        >
          {[
            partialRun.ingest,
            partialRun.enrich,
            partialRun.research,
            partialRun.draft,
          ]
            .filter(Boolean)
            .map((stage) => (
              <div key={stage!.name}>
                <span
                  style={{
                    color: stage!.status === "ok" ? "var(--pass)" : "var(--fail)",
                  }}
                >
                  {stage!.status === "ok" ? "✓" : "✗"}
                </span>{" "}
                <span style={{ color: "var(--text2)" }}>{stage!.name}</span>
                {stage!.error && (
                  <span style={{ color: "var(--fail)" }}>
                    {" "}— {stage!.error.message}
                  </span>
                )}
              </div>
            ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 10 }}>
        <Button variant="secondary" onClick={onRetry}>
          ← Try again
        </Button>
      </div>
    </div>
  );
}
