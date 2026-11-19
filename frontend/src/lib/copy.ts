/** The two sentences the screen must get exactly right, word for word as in
 * docs/decisions/0015. Kept in one place. */

export const CLAIM =
  "Every sentence of the article points at the transcript lines behind it. Code removes any sentence in which a number, date, name or quotation it can read is not in those lines or their speaker labels. A judge model then reads each sentence that is left against its lines and flags the ones it finds unsupported, and every flag is shown to the reader.";

/**
 * Whether an address may start a run by itself (`?start=`, `?rerun=`). Only on a server
 * that replays recordings: a link must never be able to start a paid run. The server's
 * mode decides, not the stored run, because a seeded run is built from recordings even
 * on a live server.
 */
export function linkMayStartRuns(config: { mode: string } | null | undefined): boolean {
  return config?.mode === "demo";
}

export const DEMO_LINE =
  "This demo replays recordings of real model calls. Nothing is generated while you watch, and nothing is spent.";
