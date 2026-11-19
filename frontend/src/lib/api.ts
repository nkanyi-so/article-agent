/** The backend's HTTP surface. Every failure becomes an `ApiError` with the backend's code. */

import { API_BASE } from "./health";
import { readEvents, type AnyEvent } from "./stream";
import type { ConfigResponse, RunDetail, RunRow, StageName } from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly retryable: boolean
  ) {
    super(code);
  }
}

/** What to tell a person for each error code. Unknown codes get the last line. */
const MESSAGES: Record<string, string> = {
  run_not_found: "There is no run with this address.",
  seed_not_found: "That transcript is not one of the seeded ones.",
  paste_disabled_in_demo:
    "This demo replays recordings, so it cannot take a pasted transcript.",
  rate_limited: "Too many runs were started from this address. Try again in a minute.",
  daily_budget_exhausted: "The day's budget for live runs is spent. Try again tomorrow.",
  replay_not_possible: "This run cannot be re-run from that stage: an earlier stage never finished.",
  transcript_empty: "The transcript is empty.",
  transcript_too_short: "The transcript is too short to write an article from.",
  transcript_too_long: "The transcript is longer than the limit.",
  transcript_unparseable: "No speaker turns were found. Each turn should start with a name and a colon.",
  no_checkable_facts: "The transcript has nothing to report: no statement that could be checked.",
  too_few_grounded_claims:
    "Fewer than three sentences of the draft survived the check, so no article is shown.",
  fixture_miss: "There is no recording for this request, so the demo cannot replay it.",
  model_refused: "The model declined to answer.",
  model_truncated: "The model's answer was cut off.",
  model_call_failed: "The model could not be reached.",
  run_timed_out: "The run took longer than its limit and was stopped.",
  stream_ended_early: "The connection closed before the run reported its result.",
  cancelled: "The run was abandoned before it finished.",
  network: "The backend could not be reached.",
};

export function messageFor(code: string | null | undefined): string {
  return (code && MESSAGES[code]) || "Something went wrong on the server.";
}

async function fail(response: Response): Promise<never> {
  let code = "internal_error";
  let retryable = false;
  try {
    const body = (await response.json()) as { error?: { code?: string; retryable?: boolean } };
    code = body.error?.code ?? code;
    retryable = body.error?.retryable ?? false;
  } catch {
    // Not the backend's error shape: keep the general code.
  }
  throw new ApiError(response.status, code, retryable);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(0, "network", true);
  }
  if (!response.ok) await fail(response);
  return response;
}

async function getJson<T>(path: string): Promise<T> {
  return (await (await request(path)).json()) as T;
}

/** Starts a stream and reads it to its terminal event. Rejects only if it never opens. */
async function stream(path: string, body: unknown, onEvent: (event: AnyEvent) => void): Promise<void> {
  const response = await request(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.body) throw new ApiError(0, "stream_ended_early", true);
  await readEvents(response.body, onEvent);
}

export const api = {
  config: (): Promise<ConfigResponse> => getJson("/api/config"),
  listRuns: async (): Promise<RunRow[]> => (await getJson<{ runs: RunRow[] }>("/api/runs")).runs,
  getRun: (id: string): Promise<RunDetail> => getJson(`/api/runs/${encodeURIComponent(id)}`),
  startSeed: (seedId: string, onEvent: (event: AnyEvent) => void): Promise<void> =>
    stream("/api/runs/stream", { seed_id: seedId }, onEvent),
  startPaste: (
    transcript: string,
    title: string,
    onEvent: (event: AnyEvent) => void
  ): Promise<void> => stream("/api/runs/stream", { transcript, title }, onEvent),
  replay: (runId: string, from: StageName, onEvent: (event: AnyEvent) => void): Promise<void> =>
    stream(`/api/runs/${encodeURIComponent(runId)}/replay/stream`, { from_stage: from }, onEvent),
};
