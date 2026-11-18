# Profile: public portfolio piece

Add these on top of the base harness when the project is a public demo of a client pattern.

## Honesty

- The README says plainly that it is a rebuild on synthetic data, and what is real versus seeded.
- Synthetic means synthetic: no real people and no real companies in seeds, fixtures, tests or eval cases. Public figures count. Invented statements about a named real person are the worst case. This holds for the git history too, so check it before a repository is made or kept public; a later commit does not remove what an earlier one published.
- The hosted demo must work with no keys on the visitor's side and still load months later. Prefer nothing that can pause or expire.

## README sections (same on every piece)

1. Run it
2. Before (the problem, in one paragraph)
3. Decisions (with links to `docs/decisions/`)
4. Evals (the table, the date it was run, one real failure and its fix)
5. Surviving production
6. How this was built (the harness, the phase pull requests, what the reviewer caught)
7. What I'd do next

## Evals

If the first live run scores 100% everywhere, the set is too easy. Add harder cases until something fails, fix it, and keep the before and after.

## Done when

The hosted page loads. The eval table is in the README with a date. CI is green on `main`. A short walkthrough video is recorded.
