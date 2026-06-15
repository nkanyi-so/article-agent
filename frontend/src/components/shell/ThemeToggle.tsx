"use client";

import { useState } from "react";
import { DEFAULT_THEME, THEME_KEY, type Theme } from "@/lib/theme";

export function ThemeToggle() {
  // Lazy initialiser reads the DOM attribute set by ThemeScript — matches the
  // server-rendered default without a useEffect flash.
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof document === "undefined") return DEFAULT_THEME;
    return (document.documentElement.getAttribute("data-theme") as Theme) ?? DEFAULT_THEME;
  });

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
