/** Asks the backend whether it is up and which mode it runs in. Never throws. */

export type BackendHealth =
  | { reachable: true; mode: string; version: string }
  | { reachable: false };

// The fallback is for local development. A build on the host without the variable
// fails in next.config.ts, so a deployed page can never point at localhost.
export const API_BASE: string = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

function isHealthBody(body: unknown): body is { status: "ok"; mode: string; version: string } {
  if (typeof body !== "object" || body === null) return false;
  const candidate = body as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    typeof candidate.mode === "string" &&
    typeof candidate.version === "string"
  );
}

export async function fetchHealth(
  base: string = API_BASE,
  fetchImpl: typeof fetch = fetch
): Promise<BackendHealth> {
  try {
    const response = await fetchImpl(`${base}/health`, { cache: "no-store" });
    if (!response.ok) return { reachable: false };
    const body: unknown = await response.json();
    if (!isHealthBody(body)) return { reachable: false };
    return { reachable: true, mode: body.mode, version: body.version };
  } catch {
    // A network failure and a blocked cross-origin request look the same from here.
    return { reachable: false };
  }
}
