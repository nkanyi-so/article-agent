"use client";

import { useEffect, useState } from "react";
import { DEFAULT_THEME, THEME_KEY, type Theme } from "@/lib/theme";

export function ThemeToggle() {
  // Must start with DEFAULT_THEME so the server-rendered HTML matches the
  // initial client render exactly (React 19 won't patch hydration mismatches).
  // useEffect then syncs to whatever ThemeScript wrote to data-theme before
  // React loaded — this corrects the toggle button after first paint without
  // any page-level flash.
  const [theme, setTheme] = useState<Theme>(DEFAULT_THEME);

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme") as Theme | null;
    if (current && current !== theme) setTheme(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyTheme(next: Theme) {
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Private browsing / storage blocked — fail silently.
    }
    setTheme(next);
  }

  return (
    <div
      style={{
        display: "flex",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "3px",
        gap: "2px",
      }}
    >
      {(["dark", "light"] as Theme[]).map((t) => (
        <button
          key={t}
          onClick={() => applyTheme(t)}
          style={{
            padding: "3px 10px",
            borderRadius: "6px",
            border: theme === t ? "1px solid var(--border2)" : "1px solid transparent",
            background: theme === t ? "var(--surface2)" : "transparent",
            color: theme === t ? "var(--text)" : "var(--text3)",
            fontSize: "12px",
            fontWeight: 500,
            cursor: "pointer",
            fontFamily: "inherit",
            lineHeight: 1.4,
          }}
        >
          {t.charAt(0).toUpperCase() + t.slice(1)}
        </button>
      ))}
    </div>
  );
}
