/**
 * Typed API client for the article-agent backend.
 *
 * All fetch calls use { cache: "no-store" } (Next.js 16 default is uncached;
 * this is explicit for clarity).
 */

import type { FormRequest, HealthResponse, Run, RunsResponse } from "./run-types";
import type { PipelineEvent, StreamHandlers } from "./stream-types";

const BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

// ── Error class ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
    public readonly retryable?: boolean,
    public readonly body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Internal helpers ─────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    const detail = body && typeof body === "object" && "detail" in body
      ? body.detail
      : null;
    const msg =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail !== null && "message" in detail
        ? String((detail as Record<string, unknown>)["message"])
        : `HTTP ${res.status}`;
    const code =
      typeof detail === "object" && detail !== null && "code" in detail
        ? String((detail as Record<string, unknown>)["code"])
        : undefined;
    const retryable =
      typeof detail === "object" && detail !== null && "retryable" in detail
        ? Boolean((detail as Record<string, unknown>)["retryable"])
        : undefined;
    throw new ApiError(res.status, msg, code, retryable, body);
  }

  return res.json() as Promise<T>;
}

// ── Public API ───────────────────────────────────────────────────────────────

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  async listRuns(): Promise<Run[]> {
    const data = await request<RunsResponse>("/api/runs");
    return data.runs;
  },

  async getRun(id: string): Promise<Run> {
    const data = await request<{ run: Run }>(`/api/runs/${id}`);
    return data.run;
  },

  /**
   * Non-streaming run creation. Branch on run.status, not HTTP status:
   * - "completed" → article is ready
   * - "needs_disambiguation" → enrich.output.candidates populated
   * - "failed" → error attached (the HTTP 4xx/5xx also throws ApiError)
   */
  async createRun(form: FormRequest, evaluate = false): Promise<Run> {
    const qs = evaluate ? "?evaluate=true" : "";
    const data = await request<{ run: Run }>(`/api/runs${qs}`, {
      method: "POST",
      body: JSON.stringify(form),
    });
    return data.run;
  },

  /** Upgrade a stored run to a full 4-verdict eval report. */
  async runEvals(id: string): Promise<Run> {
    const data = await request<{ run: Run }>(`/api/runs/${id}/evals`, {
      method: "POST",
    });
    return data.run;
  },

  /**
   * Stream a pipeline run via SSE (POST /api/runs/stream).
   *
   * Uses fetch + ReadableStream (not EventSource, which is GET-only).
   * Dispatches typed handlers as events arrive. Returns an AbortController
   * so the caller can cancel mid-stream (e.g. on component unmount).
   *
   * Branch run outcome on the event type, NOT HTTP status.
   */
  streamRun(
    form: FormRequest,
    evaluate: boolean,
    handlers: StreamHandlers
  ): AbortController {
    const controller = new AbortController();

    (async () => {
      let res: Response;
      try {
        res = await fetch(
          `${BASE}/api/runs/stream${evaluate ? "?evaluate=true" : ""}`,
          {
            method: "POST",
            signal: controller.signal,
            cache: "no-store",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(form),
          }
        );
      } catch (err) {
        if ((err as { name?: string }).name === "AbortError") return;
        handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
        return;
      }

      if (!res.ok) {
        let body: unknown;
        try { body = await res.json(); } catch { body = null; }
        handlers.onError?.(new ApiError(res.status, `HTTP ${res.status}`, undefined, undefined, body));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        handlers.onError?.(new Error("No response body"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by double newlines.
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            const parsed = parseSSEBlock(block);
            if (parsed) dispatchEvent(parsed, handlers);
          }
        }
      } catch (err) {
        if ((err as { name?: string }).name === "AbortError") return;
        handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
      } finally {
        reader.releaseLock();
      }
    })();

    return controller;
  },
};

// ── SSE parsing ───────────────────────────────────────────────────────────────

function parseSSEBlock(block: string): PipelineEvent | null {
  let eventName = "";
  let dataStr = "";

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataStr = line.slice("data:".length).trim();
    }
  }

  if (!eventName) return null;

  let data: unknown = {};
  if (dataStr) {
    try {
      data = JSON.parse(dataStr);
    } catch {
      return null;
    }
  }

  return { event: eventName, data } as PipelineEvent;
}

function dispatchEvent(event: PipelineEvent, handlers: StreamHandlers): void {
  switch (event.event) {
    case "run_started":
      handlers.onRunStarted?.(event.data);
      break;
    case "stage_started":
      handlers.onStageStarted?.(event.data);
      break;
    case "stage_completed":
      handlers.onStageCompleted?.(event.data);
      break;
    case "needs_disambiguation":
      handlers.onNeedsDisambiguation?.(event.data);
      break;
    case "evaluating":
      handlers.onEvaluating?.(event.data);
      break;
    case "run_completed":
      handlers.onCompleted?.(event.data);
      break;
    case "run_failed":
      handlers.onFailed?.(event.data);
      break;
  }
}
