import { describe, expect, it } from "vitest";
import { applyEvent, startLiveRun, type LiveRun } from "./live";
import { EventParser, readEvents, type AnyEvent } from "./stream";

const started = { seq: 0, at: "2026-11-19T06:00:00+00:00", run_id: "r1", type: "run_started" };
const stage = { seq: 1, at: "2026-11-19T06:00:00+00:00", run_id: "r1", type: "stage_started", stage: "ingest" };
const completed = { seq: 2, at: "2026-11-19T06:00:01+00:00", run_id: "r1", type: "run_completed" };
const sse = (event: object): string => `data: ${JSON.stringify(event)}\n\n`;

function bodyOf(chunks: string[], thenFail = false): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const pending = [...chunks];
  // One chunk a read, so an error arrives after the chunks before it have been read.
  return new ReadableStream({
    pull(controller) {
      const next = pending.shift();
      if (next !== undefined) controller.enqueue(encoder.encode(next));
      else if (thenFail) controller.error(new Error("connection reset"));
      else controller.close();
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>): Promise<AnyEvent[]> {
  const events: AnyEvent[] = [];
  await readEvents(body, (event) => events.push(event));
  return events;
}

describe("the event parser", () => {
  it("reads data-only events, however the text is cut into chunks", () => {
    const text = sse(started) + sse(stage) + sse(completed);
    for (const size of [1, 7, 50, text.length]) {
      const parser = new EventParser();
      const events = [];
      for (let at = 0; at < text.length; at += size) events.push(...parser.push(text.slice(at, at + size)));
      expect(events.map((event) => event.type)).toEqual(["run_started", "stage_started", "run_completed"]);
    }
  });

  it("accepts CRLF line endings and ignores comments and unknown fields", () => {
    const parser = new EventParser();
    const events = parser.push(`: keep-alive\r\n\r\nid: 4\r\ndata: ${JSON.stringify(started)}\r\n\r\n`);
    expect(events).toEqual([started]);
  });

  it("drops what is not one of the five events: bad JSON, another type, no run id", () => {
    const parser = new EventParser();
    const events = parser.push(
      "data: {not json\n\n" + sse({ type: "something_else", run_id: "r1" }) + sse({ type: "run_started" }) + sse(started)
    );
    expect(events).toEqual([started]);
  });
});

describe("reading a stream", () => {
  it("ends with the stream's own terminal event and nothing after it", async () => {
    const events = await collect(bodyOf([sse(started), sse(completed), sse(stage)]));
    expect(events.map((event) => event.type)).toEqual(["run_started", "run_completed"]);
  });

  it("says so when the stream closes with no terminal event", async () => {
    const events = await collect(bodyOf([sse(started), sse(stage)]));
    expect(events.at(-1)).toEqual({ type: "stream_ended_early", run_id: "r1" });
  });

  it("says so when the connection drops mid-stream", async () => {
    const events = await collect(bodyOf([sse(started)], true));
    expect(events.at(-1)).toEqual({ type: "stream_ended_early", run_id: "r1" });
  });

  it("says so when the stream is empty, with no run to name", async () => {
    expect(await collect(bodyOf([]))).toEqual([{ type: "stream_ended_early", run_id: null }]);
  });
});

describe("folding events into the five stages", () => {
  const fold = (events: object[]): LiveRun =>
    events.reduce<LiveRun>((run, event) => applyEvent(run, event as AnyEvent), startLiveRun());

  it("moves a stage from waiting to running to done, and marks a copied one", () => {
    const run = fold([
      started,
      { ...stage, type: "stage_completed", stage: "ingest", duration_ms: 3, copied_from_run_id: "seed-a" },
      { ...stage, stage: "extract" },
      { ...stage, type: "stage_completed", stage: "extract", duration_ms: 1200, copied_from_run_id: null },
      { ...stage, stage: "draft" },
    ]);
    expect(run.runId).toBe("r1");
    expect(run.stages.map((s) => s.status)).toEqual(["copied", "done", "running", "waiting", "waiting"]);
    expect(run.stages[1]?.durationMs).toBe(1200);
    expect(run.ended).toBeNull();
  });

  it("ends failed, with the stage that was running marked, on run_failed", () => {
    const run = fold([started, stage, { ...completed, type: "run_failed", error: "transcript_too_short", stage: "ingest" }]);
    expect(run.stages[0]?.status).toBe("failed");
    expect(run.ended).toEqual({ ok: false, error: "transcript_too_short" });
  });

  it("ends failed when the stream stops early, and never stays running", () => {
    const run = fold([started, stage, { type: "stream_ended_early", run_id: "r1" }]);
    expect(run.stages.some((s) => s.status === "running")).toBe(false);
    expect(run.ended).toEqual({ ok: false, error: "stream_ended_early" });
  });
});
