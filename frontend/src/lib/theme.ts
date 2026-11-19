/** Shared theme constants — used by ThemeScript (server) and ThemeToggle (client). */

export const THEME_KEY = "theme" as const;
export type Theme = "dark" | "light";
export const DEFAULT_THEME: Theme = "dark";

/** The inline script that reads localStorage before first paint (no FOUC). */
// `?theme=light` or `?theme=dark` in the address wins over the stored choice, without
// changing it: a link (or a screenshot) can ask for one theme.
export const THEME_INIT_SCRIPT = `(function(){try{var q=new URLSearchParams(location.search).get('theme');var t=(q==='dark'||q==='light')?q:localStorage.getItem('${THEME_KEY}');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t)}catch(e){}})()`;
