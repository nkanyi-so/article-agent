# 0011: keep the Next.js shell, cut the showcase page, add a test runner

**Status:** proposed, 2026-11-18

**Context.** `frontend/` is the old Next.js app, 4,203 lines, ported as working code: it type-checks and builds, lint fails on three errors, there are no tests, and it still contains the name-lookup UI. Checked on 2026-11-18: Next.js 16.4.6 is the latest stable (the app is on 16.2.9, two minor versions back; 16.4 ships React 19.3 and changes some build defaults; neither release post lists breaking changes); Node 20 is end-of-life and this machine runs 20.18; Vitest 5.1.1 needs Node 22.12 or later; `@testing-library/react` 16 supports React 19.

**Decision.**

- **Keep** the shell, sidebar, theme, primitives, run page layout, eval cards and the stream reader. Rewrite the entry form, the article view and the trace against the new API when the screen is built.
- **Cut `/design-system`.** It is 570 lines, linked from nowhere, carries one of the three lint errors, and shows components the run page already shows in use. It does nothing for the claim, and a reader with two minutes should not be offered a detour.
- **Node 24** pinned for the frontend and CI. I install it during project setup.
- **Upgrade to the current Next.js 16.4 patch during project setup**, while the app is still unchanged and the only thing that can break is the build. The bundled guide is read first. If the build breaks, stay on 16.2.9 and log why.
- **Vitest** for unit tests: the stream parser and claim-to-segment rendering.
- **Styling stays** as inline styles over CSS variables. Tailwind 4 stays too: no utility classes are used, but `globals.css` imports it, so its base reset and theme block shape every page. Removing it is a visual change with no test to catch it, and it is a build-time dependency only.
- **Fix, do not quarantine,** the three lint errors during project setup.

**Consequence.** The frontend work is a rewrite of three views inside a kept shell, not a new app. The name-lookup files listed in the original brief are deleted there, and `git grep` for the old vendor names must come back empty once it is done. Revisit the showcase page only if it is wanted for a design portfolio; it is in the legacy repository's history.
