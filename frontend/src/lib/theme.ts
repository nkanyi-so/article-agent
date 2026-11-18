/** Shared theme constants — used by ThemeScript (server) and ThemeToggle (client). */

export const THEME_KEY = "theme" as const;
export type Theme = "dark" | "light";
export const DEFAULT_THEME: Theme = "dark";

/** The inline script that reads localStorage before first paint (no FOUC). */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('${THEME_KEY}');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}})()`;
