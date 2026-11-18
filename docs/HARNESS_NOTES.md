# Harness notes

Friction with the harness on this project, logged as it happens. One line each: date, what happened, what the harness should do differently. `/harness-retro` reads this.

## Intake run, harness 0.3.0

- 2026-11-18. The intake was first started in the wrong folder (the legacy repository, where the session was opened) while the brief said "in this folder". The skill has no step that checks the brief exists where it is told to look before doing anything else. Suggest: step 0, confirm the project folder and stop if the named brief is not in it.
- 2026-11-18. Working on a project that is not the session's working directory means the session's hooks, deny rules and agent definitions are the other project's. The new layer applied by `apply.sh` was not active for this run. The skill should say to open the session in the project folder.
- 2026-11-18. "Add the remote before the first commit so the right identity is used" assumes the remote exists. With two GitHub accounts logged in, the active one was the wrong one; the skill should say to check `gh api user` against the intended owner before creating the repository.
- 2026-11-18. The Phase 0 template gate "branch protection is shown to be on" may be impossible on a private repository on a free GitHub plan. The plan here gives the owner the choice (pay, or carry the item to the release phase). The template should carry that branch.
- 2026-11-18. The skill says "check current docs for every library before naming it". Doing that for hosting, the model API and the toolchain took three research agents and most of the run's wall-clock time. Worth saying in the skill that this is the expected cost, and that the agents' quotes arrive through a summarising fetch and need re-reading before they are quoted publicly.
- 2026-11-18. The template has no place for "steps that spend money or act outside this machine" or "what a merge deploys". The adopt skill gained both in 0.3.0; the intake template should too. Added by hand at the top of `docs/PLAN.md`.
- 2026-11-18. The skill does not say whether the intake should commit its output. The owner's rule is no commit without approval, so nothing was committed; the blueprint sits uncommitted in the working tree.

## Phase 0, harness 0.3.0

- 2026-11-18. The Phase 0 template step "adapt the allow list in `.claude/settings.json`" asks the agent to widen its own permissions. The session's permission layer refused the edit outright (not the hook's "ask", a denial). The template should make this an owner step, with the lines to paste.
- 2026-11-18. The pre-commit hook runs in a non-interactive shell, where the system Node (20) came ahead of nvm's, so `make check` would have run the frontend on the wrong Node or failed. Needed a wrapper script. The template's Makefile guidance should say that hooks do not see the interactive shell's toolchain.
- 2026-11-18. The intake's blueprint is the base commit, and CI runs `make check` on every push to `main`, so the first push would have been a red run with nothing to check. Worked around with `[skip ci]` on the base commit. The template should either say so or have CI skip when there is no Makefile.
- 2026-11-18. The intake's synthetic-data pass covered the application source it changed but not `design/`, which still named real companies and real sites as sample data. The search step should say "the whole tree, every file type", and should be run by the intake before it hands over, not left to Phase 0.
- 2026-11-18. The Phase 0 step "search the tree for the real names the brief says were replaced" cannot be done as written: the brief deliberately does not contain those names. Only the owner can run that exact search. The template should ask the owner to run it, or to supply the names out of band.
- 2026-11-18. `core.hooksPath` was already set when Phase 0 started, so the pre-commit hook ran on the blueprint commit before any Makefile existed. It handled that well (warned and went on). Worth keeping.
- 2026-11-18. The pre-commit hook runs the whole gate, including the production build, on every commit. It will grow with the project. No change asked for, just noting the cost.
- 2026-11-18. `make format FILE=` is called by the edit hook for every file, but the frontend has no formatter, so for TypeScript it does nothing. The CLAUDE.md line reads as if every file is formatted.
- 2026-11-18. The skill runs the reviewer and the verifier one after the other; running them at once saved time but they collided: both ran `make check` and one ran `make dev` in the same folder, and the reviewer saw one unexplained `next build` failure it could not reproduce. Either run them in sequence or give each its own worktree.
- 2026-11-18. The verifier found that `next dev` (16.3 and later) rewrites `frontend/AGENTS.md` whenever it detects a coding agent, which dirties the tree on every `make dev`. The frontend template should ship the current managed block.
- 2026-11-18. The verifier stops `make dev` by signalling the `make` process, which orphans the servers under any Makefile. Its instructions should say to signal the process group.

## Phase 1, harness 0.3.0

- 2026-11-18. The plan's spike step counted draft calls only ("about 16"), but the owner also wanted the real cost of a whole run, which needs extract and judge calls too. The spike ran 18 billed calls. A spike template should list every kind of call a cost figure needs before the estimate is given.
- 2026-11-18. The page-fetching tool returned the first half of the citations documentation verbatim and the rest as a summary it could not vouch for, including the request shape the spike needed. The shape was confirmed by the unbilled request and the first paid call instead. Worth knowing before quoting that page in the README.
- 2026-11-18. The skill has one "stop if the findings contradict a decision record" rule and the owner asked for the phase to run through to the pull request. Resolved by writing the findings and the proposed changes, leaving the contradicted records unedited, and marking the dependent phase blocked. The skill could say that this is the expected way to hand over a spike.
- 2026-11-18. `spikes/` is outside `make check`: no lint, no types, no tests. Right for throwaway code, but the reviewer has nothing mechanical to lean on there.

