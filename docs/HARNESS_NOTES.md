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
