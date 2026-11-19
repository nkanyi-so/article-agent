/**
 * The runs this browser started, kept in the browser.
 *
 * On the hosted demo each backend instance keeps its own list of runs, so the list a
 * visitor is shown would change from one request to the next. A run's address always
 * works (the backend can make a demo run again from its id); what was missing was a list
 * that stays put. So in demo mode the list is the seeded runs plus these.
 */

export type MyRun = { id: string; title: string; kind: "run" | "re-run"; at: string };

const KEY = "article-agent.runs";
const MOST = 12;

type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    // Storage can be switched off. The list is then empty, and nothing else breaks.
    return null;
  }
}

function isMyRun(value: unknown): value is MyRun {
  if (typeof value !== "object" || value === null) return false;
  const run = value as Record<string, unknown>;
  return (
    typeof run.id === "string" &&
    /^[a-z0-9-]{1,160}$/.test(run.id) &&
    typeof run.title === "string" &&
    (run.kind === "run" || run.kind === "re-run") &&
    typeof run.at === "string"
  );
}

/** Newest first. Anything in storage that is not a run this code wrote is ignored. */
export function myRuns(from: Storage | null = storage()): MyRun[] {
  try {
    const parsed: unknown = JSON.parse(from?.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter(isMyRun).slice(0, MOST) : [];
  } catch {
    return [];
  }
}

/** Remembers a run that finished. Runs that were abandoned are never remembered. */
export function rememberRun(run: MyRun, to: Storage | null = storage()): void {
  if (!to || !isMyRun(run)) return;
  const others = myRuns(to).filter((known) => known.id !== run.id);
  try {
    to.setItem(KEY, JSON.stringify([{ ...run, title: run.title.slice(0, 200) }, ...others].slice(0, MOST)));
  } catch {
    // A full or blocked store: the run still opened, it is only missing from the list.
  }
}
