---
name: next-phase
description: Resume the build at the next unticked phase in docs/PLAN.md
argument-hint: "[extra instructions]"
disable-model-invocation: true
---
This is the working loop. It lives here and nowhere else.

1. **Where things stand.** Read CLAUDE.md and docs/PLAN.md. Find the first phase with unticked boxes. Do not start it if the previous gate is unticked. Summarise: last log entry, failing tests, open reviewer findings.
2. **Read before planning.** The SPEC and ARCHITECTURE sections the phase touches, and any file in docs/profiles/. Check current docs or installed source for every library the phase uses.
3. **Propose** the step list for the phase and the risks you see, then wait for approval.
4. **Build** on a branch for this phase. Tests first for core logic, then implement. Run `make check` and fix until it exits 0.
5. **Review.** Run the `reviewer` agent on the phase diff. Fix every blocking finding. Paste its findings into the phase log as it reported them, then what you did about each.
6. **Verify.** Run the `verifier` agent once there is something to run. Paste its table into the phase log.
7. **Evidence.** Write the gate evidence into the phase log: the commands run and their real output. Only then tick the gate.
8. **Hand over.** Commit, push, open one pull request for the phase. The description is the plan summary plus a link to the phase log. Then stop: the human reads the evidence and merges.
9. **If it stops fitting.** If the gate cannot pass, or the spec or plan turns out wrong, stop. Say what is failing and why. Changing the docs comes first: propose the edit and a decision record, wait for approval, then re-plan the phase. Never weaken the gate instead.
10. If the harness got in the way or lacked something, add a line to docs/HARNESS_NOTES.md.

Extra instructions, if any: $ARGUMENTS
