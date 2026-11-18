/** Formatting helpers — pure functions, no side-effects. */

/**
 * Convert milliseconds to a human-readable duration string.
 * e.g. 1840 → "1.84s", 250 → "250ms", 65000 → "1m 5s"
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(2)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

/**
 * Sum duration_ms across an array of objects that have it.
 */
export function totalDuration(items: Array<{ duration_ms: number }>): number {
  return items.reduce((acc, s) => acc + s.duration_ms, 0);
}

/**
 * Pretty-print any value as indented JSON string.
 * Returns an empty string for null/undefined.
 */
export function prettyJson(value: unknown): string {
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/**
 * Format an ISO 8601 string as a short human date, e.g. "Jun 15, 2026".
 * Renders on the client only (avoids server/client locale mismatch).
 */
export function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Truncate a string to maxLen characters, appending "…" if truncated.
 */
export function truncate(s: string, maxLen: number): string {
  return s.length <= maxLen ? s : s.slice(0, maxLen) + "…";
}
