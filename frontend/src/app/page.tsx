"use client";

import { useEffect, useState } from "react";

type HealthStatus = "loading" | "ok" | "error";

export default function Home() {
  const [status, setStatus] = useState<HealthStatus>("loading");
  const [detail, setDetail] = useState<string>("");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ status: string; service: string; version: string }>;
      })
      .then((data) => {
        setStatus("ok");
        setDetail(`${data.service} v${data.version}`);
      })
      .catch((err: Error) => {
        setStatus("error");
        setDetail(err.message);
      });
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-8">
      <div className="w-full max-w-sm rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-6">
          article-agent
        </h1>

        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-500 dark:text-zinc-400 w-20">Backend</span>

          {status === "loading" && (
            <span className="text-sm text-zinc-400 animate-pulse">checking…</span>
          )}
          {status === "ok" && (
            <>
              <span className="h-2 w-2 rounded-full bg-green-500 shrink-0" />
              <span className="text-sm text-zinc-700 dark:text-zinc-300">{detail}</span>
            </>
          )}
          {status === "error" && (
            <>
              <span className="h-2 w-2 rounded-full bg-red-500 shrink-0" />
              <span className="text-sm text-red-600 dark:text-red-400">{detail}</span>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
