"use client";

import { useSyncExternalStore } from "react";
import { DEFAULT_THEME, THEME_KEY, type Theme } from "@/lib/theme";

// The theme lives on <html data-theme>, written by ThemeScript before React loads
// and by the toggle afterwards. Reading it as an external store keeps the server
// render on DEFAULT_THEME (so hydration matches) and then follows the attribute.
function subscribeToTheme(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return () => observer.disconnect();
}

function readTheme(): Theme {
  const current = document.documentElement.getAttribute("data-theme");
  return current === "dark" || current === "light" ? current : DEFAULT_THEME;
}

function readServerTheme(): Theme {
  return DEFAULT_THEME;
}

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeToTheme, readTheme, readServerTheme);

  function applyTheme(next: Theme) {
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Private browsing / storage blocked — fail silently.
    }
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
