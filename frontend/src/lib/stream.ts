/**
 * Reads a run's event stream.
 *
 * The backend sends data-only server-sent events: each event is one `data:` line of JSON
 * with its kind in `type`. Every stream is meant to end with `run_completed` or
 * `run_failed`. If the connection drops first, the reader says so with an event of its
 * own, so the screen is never left waiting on a run that will not report again.
 */

import type { RunEvent } from "./types";

export type StreamEnded = { type: "stream_ended_early"; run_id: string | null };
export type AnyEvent = RunEvent | StreamEnded;

const KINDS = new Set(["run_started", "stage_started", "stage_completed", "run_completed", "run_failed"]);
const TERMINAL = new Set(["run_completed", "run_failed"]);

function isEvent(value: unknown): value is RunEvent {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.type === "string" &&
    KINDS.has(candidate.type) &&
    typeof candidate.run_id === "string"
  );
}

/** Turns chunks of stream text into events. Chunks may split an event anywhere. */
export class EventParser {
  private buffer = "";

  push(chunk: string): RunEvent[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const events: RunEvent[] = [];
    let end = this.buffer.indexOf("\n\n");
    while (end !== -1) {
      const block = this.buffer.slice(0, end);
      this.buffer = this.buffer.slice(end + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) {
        try {
          const parsed: unknown = JSON.parse(data);
          // Anything that is not one of the five known events is ignored, not trusted.
          if (isEvent(parsed)) events.push(parsed);
        } catch {
          // A malformed event is dropped. The missing terminal event is what gets reported.
        }
      }
      end = this.buffer.indexOf("\n\n");
    }
    return events;
  }
}

/**
 * Reads a response body to its end, calling `onEvent` for each event. Always finishes
 * with exactly one terminal event: the stream's own, or `stream_ended_early`.
 */
export async function readEvents(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: AnyEvent) => void
): Promise<void> {
  const parser = new EventParser();
  const decoder = new TextDecoder();
  const reader = body.getReader();
  let runId: string | null = null;
  let finished = false;
  try {
    while (!finished) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) {
        runId = event.run_id;
        onEvent(event);
        if (TERMINAL.has(event.type)) {
          finished = true;
          break;
        }
      }
    }
  } catch {
    // A dropped connection. Reported below as an early end.
  } finally {
    reader.cancel().catch(() => undefined);
  }
  if (!finished) onEvent({ type: "stream_ended_early", run_id: runId });
}
