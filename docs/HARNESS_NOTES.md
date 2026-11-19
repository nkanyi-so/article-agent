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

## Phase 2, harness 0.3.0

- 2026-11-18. The plan says "connect two Vercel projects to the repository" as if the agent can. Connecting needs Vercel's GitHub app to have access to the private repository, which is the owner's setting. The plan template should list it under "owner actions" with the phase that needs it.
- 2026-11-18. A Vercel project created from the command line has no framework preset, and the first deploy of each side built nothing and served 404 with a green "Ready". A deploy step should always be followed by a request that proves a route answers.
- 2026-11-18. A cold start cannot be measured right after a deploy: the platform had already started an instance before the first request. It needs an idle wait, which the harness has no patient way to do; a background timer was used, and every other check had to be kept away from the deployed address meanwhile.
- 2026-11-18. Follow-up work from the previous phase's review (the owner's decisions, a re-run) had no home: the skill is one branch and one pull request per phase. It went in as its own commit at the start of this phase's branch. The skill could name that as the place.
- 2026-11-18. The reviewer caught that "never `*`" for CORS was only a comment. A rule stated in a comment and not enforced is worth a line in the reviewer's checklist.

## Phase 3, harness 0.3.0

- 2026-11-18. The format-on-edit hook rewrites a file straight after it is written, so a scripted follow-up edit that matched the text as written silently missed lines the formatter had re-wrapped. Three rounds of fixes. Either the hook should report what it changed, or scripted edits should always re-read first.
- 2026-11-18. Test-first held up: of the three failures on the first full run, two were mistakes in the tests' own expectations and one was a real gap (a draft with no headline line was read as having one). Worth saying in the skill that a failing new test is checked against the spec before the code is changed.
- 2026-11-18. The gate asks for "the test list shows each removal rule failing a hand-altered response and passing the real one". Naming the tests `rule_N_real_...` and `rule_N_altered_...` made that list readable without opening the file. The template could ask for that convention.
- 2026-11-18. The owner's new rule (check both production deploys after every merge, and log it) belongs in the skill's hand-over step for any project where a merge deploys. It is written at the top of the plan for now.
- 2026-11-18. The real drafts contain nothing false, so "what the check catches" can only be shown on altered copies, and everything it removes from real drafts is a cost. A phase that builds a checker should plan for that up front: it needs negatives made by hand, or it has nothing to catch.
- 2026-11-18. Asking the reviewer to break the checker, with a list of attack ideas, found three real holes and nine smaller ones that reading the diff would not have. For any phase whose product is a check, the reviewer's brief should say "try to get a false one through" as standard.
- 2026-11-18. A file write was refused because the format hook had changed the file since it was last read, and the refusal was easy to miss among the test output: the next test run failed 73 tests against the old file. The harness could make a refused write louder than a failed test.

## Phase 4, harness 0.3.0

- 2026-11-19. A prompt that cleared the owner's bar (2.1% removed) had its worked examples lifted from the test transcripts; with neutral examples it measured 6.6%. Nothing in the harness would have caught it: it was noticed while writing the decision record. A test now fails if a prompt contains a name from a seeded or fixture transcript. The llm-app profile should carry that rule: examples in a prompt never come from the eval or seed data.
- 2026-11-19. "Stop and bring options if the bar is not met" worked as an instruction, but only because the bar was a number. The plan template should ask for a measurable bar on any step that tunes a prompt.
- 2026-11-19. A one-word prompt edit and its restore, made in the same second with the same file length, left a stale bytecode cache: Python kept running the edited prompt after the file was restored, and ten tests failed against a file that was correct on disk. Any "change it, show it fails, change it back" demonstration should clear `__pycache__` or touch the file afterwards.
- 2026-11-19. A long shell command chained with `&&` stopped at an early failing step, so a file later steps needed was never written, and the failure showed up as an unrelated import error. Fewer, shorter commands per step.
- 2026-11-19. The spend ledger with a hard stop (`tools/spend.py`) made the owner's limit real across tools and runs, and made "what did this phase cost" a one-line sum. The harness could ship that as a pattern for any paid step.
- 2026-11-19. The seeds had to be recorded twice because the prompt changed after the first recording. Recording belongs after the prompt is decided; the plan lists it as its own step but not that it must be the last one.
- 2026-11-19. A scripted edit stopped at its first failed match, and the commit that followed in the same command went through without the changes it was meant to carry (the verifier's table and the gate entry). Caught on the next line of output and fixed with a second commit. A commit should never be chained after an edit whose success has not been read.
- 2026-11-19. The reviewer, asked to attack a rule the owner had specified in one sentence, found it matching "will" to a speaker called Will and "June" to a speaker called June. A rule that sounds complete in a sentence needs adversarial inputs before it is trusted.

## Phase 5, harness 0.3.0

- 2026-11-19. Tests that send requests one after another said the rate limit worked; the reviewer sent ten at once and all ten passed a limit of two. Any guard that counts then records needs a concurrent test, and the reviewer's brief should always include "send them at once".
- 2026-11-19. The schema offered a stage name the runner does not run yet, so a request that was valid by the published schema produced a stream with no terminal event. Types shared between "what exists in the design" and "what a caller may ask for" need to be separate.
- 2026-11-19. Getting one error shape for an over-large body took four attempts, because the framework handles a declared length, a counted body and exceptions raised while reading the body in three different places. Reading the installed framework's source was faster than guessing; the skill's "check the installed source" step earned its place.
- 2026-11-19. After the Phase 4 slip, every scripted edit in this phase printed its exit status and was read before the next step, and the commit was its own command. No repeat.
- 2026-11-19. The owner asked for a hands-on walkthrough before approving. The hand-over step could always include "how to try it yourself in two minutes, and what is not built yet".

## Phase 6, harness 0.3.0

- 2026-11-19. An agent launched with remote isolation, to act as a visitor from another network, ran on this machine: it reported this machine's hostname and public address. Its result looked like a finding about the rate limit until that was checked. Any test that depends on where a request comes from should print where it came from first.
- 2026-11-19. The instruction for the phase was "run through to the open pull request without waiting", and the gate could not pass without changing what the spec says the judge is shown. The skill's step 9 (stop, propose the doc change, wait) won, and the cost of stopping was kept down by running a small paid trial of the options first, so the owner decides on numbers. The skill could say that outright: when stopped at a gate, bring measurements of the options, not only the options.
- 2026-11-19. The first fix was a prompt rule and it moved the wrong way. At about 15 sentences a case and one run a case, the eval cannot show a small improvement from a prompt change; two cases moved by 0.2 between runs with no cause. The plan template should ask how many repeats a threshold needs before a fix is measured against it.
- 2026-11-19. Putting the eval set into `make check` means a failing eval blocks the commit, which is right, but it also means a phase that ends "failed honestly, here is the evidence" cannot be put in a pull request for the owner to read. The harness has no way to hand over work that is correct and not passing.
- 2026-11-19. One of my own hand labels for the judge was wrong by the judge's stated rule, and the judge caught it. Hand-labelled pairs need a second read against the rule they are meant to test, by someone other than the person who wrote the rule.
- 2026-11-19. The reviewer, asked to get a wrong result reported as a pass, found the spend stop checking a measured figure where it should check the worst case, and a threshold applied to a pooled mean where the spec said every pass. Both were in code written after the owner's decisions, in a hurry to run. A guard on spend and a threshold are the two places to slow down.
- 2026-11-19. Running a paid tool with the `live` dependency group leaves the SDK in the local environment, so "the import fails" stops being true on the developer's machine. The verifier noticed. `make setup` or `make check` could sync the environment back.

## Phase 7, harness 0.3.0

- 2026-11-19. Looking at screenshots found four real faults that type-check, lint, tests and a build had all passed: sentences that did not wrap, a clipped phone layout, progress shown off-screen, and two lists in no shot. For a phase whose product is a screen, "take the screenshots and look at them" belongs in the working loop, not only in the hand-over.
- 2026-11-19. A stale server cost an hour: a process named differently from the command that started it survived a kill, and served a build that had been replaced under it. The symptom (pages that never left "Loading") looked like an application bug. Before debugging a page, check which process is serving it and when it started.
- 2026-11-19. The demo's recordings had no flagged sentence, so the state the owner most wanted shown did not exist in the demo's data. The plan's Phase 7 list did not ask "does the seeded data exercise every state the screen has". It should.
- 2026-11-19. The reviewer found that a link could start a paid run on a live server: the guard read a property of the stored run where it needed the server's mode. Two phases running, the reviewer's adversarial brief has found a spend path.

## Phase 8, harness 0.3.0

- 2026-11-19. Every hosted check since Phase 2 had been made with `curl`, which kept landing on one instance. The first check with a real browser found that a visitor's finished run could not be opened. "Check it the way a visitor arrives" should be in the plan from the phase that first deploys, not the phase that shows it to people.
- 2026-11-19. A phase whose gate is "verified on the hosted address" cannot pass before its own merge when a merge is the only way to deploy. The plan should either allow a preview that the check can run against (the preview frontend cannot call the preview backend here: CORS and the API address are production's) or word the gate as "after merge".
- 2026-11-19. A real-browser check written as a small script over the DevTools protocol, with no dependency, found two faults the screenshots and the logic tests had not: the run that could not be opened, and a page wider than a phone's screen. It also had four faults of its own first (clicking the middle of a wrapped sentence, reading capitals as mixed case). A check needs checking against a page known to be right.

