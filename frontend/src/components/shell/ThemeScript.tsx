/**
 * Server Component — emits an inline <script> that reads localStorage.theme
 * and sets data-theme on <html> before the first paint, preventing FOUC.
 *
 * Must be rendered inside <head> in the root layout.
 */
import { THEME_INIT_SCRIPT } from "@/lib/theme";

export function ThemeScript() {
  return (
    <script
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
    />
  );
}
