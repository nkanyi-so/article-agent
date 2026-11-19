/**
 * A stored run, by its address: reloads, shared links and the sidebar all land here.
 * A client component, because the run is fetched from the backend in the browser.
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Spinner } from "@/components/primitives/Spinner";
import { RunScreen } from "@/components/run/RunScreen";
import { api, ApiError, messageFor } from "@/lib/api";
import type { RunDetail } from "@/lib/types";

// What was loaded, and for which address. While `id` differs from the current address a
// load is in flight, so "loading" needs no state of its own.
type Loaded =
  | { id: string; state: "ready"; run: RunDetail }
  | { id: string; state: "error"; code: string; missing: boolean };

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  useEffect(() => {
    if (!id) return;
    let stale = false;
    api
      .getRun(id)
      .then((run) => {
        if (!stale) setLoaded({ id, state: "ready", run });
      })
      .catch((error: unknown) => {
        if (stale) return;
        // A run that does not exist and a backend that cannot be reached are different
        // things, and are said differently.
        const code = error instanceof ApiError ? error.code : "internal_error";
        setLoaded({ id, state: "error", code, missing: code === "run_not_found" });
      });
    return () => {
      stale = true;
    };
  }, [id]);

  if (loaded === null || loaded.id !== id) {
    return (
      <div className="page" style={{ display: "flex", gap: 12, alignItems: "center", color: "var(--text3)" }}>
        <Spinner size={18} />
        Loading the run…
      </div>
    );
  }
  if (loaded.state === "error") {
    return (
      <div className="page">
        <div className="note-removed" role="alert">
          <div className="micro" style={{ color: "var(--fail)", marginBottom: 4 }}>
            {loaded.missing ? "No such run" : "The run could not be loaded"}
          </div>
          {messageFor(loaded.code)}{" "}
          <Link className="link" href="/">
            Back to the transcripts
          </Link>
        </div>
      </div>
    );
  }
  // Keyed by the run, so a re-run opens with nothing chosen from the run before it.
  return <RunScreen key={loaded.run.run.id} run={loaded.run} />;
}
