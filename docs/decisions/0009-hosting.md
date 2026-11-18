# 0009: hosting on Vercel Hobby, backend in demo mode

**Status:** accepted by the owner on 2026-11-18: Vercel Hobby for both, Fly.io as the fallback if Phase 2 shows the stream buffering. **Phase 2 proved it** (see "What Phase 2 found" below).

**Context.** The owner chose design A: a real backend in demo mode, so the hosted site runs the real pipeline. The host must not stop, must be free or close to it, and must never be a trial plan. The old deployment died because its backend host was on a trial and stopped the service a month after the last deploy, while the frontend stayed up pointing at nothing. The workload is tiny: no outbound calls, a few requests a day, an event stream that lasts seconds.

Hosts compared on 2026-11-18 from their own pricing and documentation pages. Most pages were read through a summarising fetch tool; re-read before quoting in the README.

| Host | Cost | Stops or expires | Disk | Verdict |
|---|---|---|---|---|
| **Vercel Hobby, Python runtime** | $0, no card. Cannot bill: when limits are hit it waits, it does not charge. | No inactivity pause documented. Idle functions are archived and wake on the next request, about a second slower. | None. Read-only bundle plus a writable scratch folder per instance. | **Proposed.** |
| **Fly.io**, smallest machine always on, 1 GB volume | About $2.35 a month ($2.19 machine, $0.15 volume). Card required. Their pricing page says a personal bill under $5 is waived. | No free tier, not a trial once on pay-as-you-go. No hard spend cap, but one fixed machine bounds it. | Yes | **The paid alternative.** |
| Google Cloud Run | $0 inside a free tier with no end date | Scales to zero, wakes on request | None | Needs a billing account and has no hard cap: budgets only alert. Same no-disk limit as Vercel with more exposure. |
| Northflank free sandbox | $0, claims always on | Not verified beyond the pricing page | Not checked | Unverified; not chosen on one page. |
| Render free | $0 | Sleeps after 15 minutes, about a minute to wake; suspended when monthly hours run out | None | Wake time fails the two-minute reader. |
| Railway | $1 of credit a month on the free plan; $5 trial grant | Stops when credit runs out | Yes | This is what failed before. |
| Koyeb, Hugging Face Docker Spaces, Cloudflare Containers | No free compute, paid plan to create, $5 floor | | | Ruled out on cost. |
| Oracle Always Free VM | $0 | Reclaims idle instances, and this workload is idle by design | Yes | Ruled out. |

Vercel specifics checked: Python 3.12, 3.13 and 3.14; FastAPI deploys natively; "Vercel Functions support streaming responses when using the Python runtime"; maximum duration on Hobby is 300 seconds; bundle limit 500 MB; "a file-based database such as SQLite can't persist your application's data in a function". Hobby is for "personal or non-commercial use", which a portfolio piece is.

**Decision.** Both the frontend and the backend on Vercel Hobby, as two projects from one repository, the backend in demo mode with the base dependency set only.

**Why.** It is the only option that is not a trial, needs no card, cannot bill, and has no documented inactivity pause. It is also the platform the frontend is already on, so there is no second account or second bill that can lapse on its own, which is exactly how the old demo broke.

**What it costs: no disk.** A run a visitor starts is stored in that instance's scratch database and is gone when the instance is. The design absorbs this honestly:

- Seeded runs are rebuilt at every start by running the real pipeline with the fixture client, under stable ids, so their links always work.
- In demo mode a run of a seeded transcript is deterministic, so nothing a visitor made is lost that cannot be made again in a second.
- The run page renders from the stream's final event, not from a second request that might reach another instance.
- The UI says that runs started on the hosted demo are not kept, and that they are kept when run locally.

So on the hosted site, "saved runs" is true of the seeded runs and of the store code that serves them; durable visitor runs are true only locally. The README says exactly that.

**The alternative, with its price.** If the owner wants visitor runs to be durable on the hosted site, the answer is Fly.io at about $2.35 a month, likely waived under their sub-$5 policy, with a card on file. It is a real always-on container with a disk and no cold start. It adds a second platform and a billing relationship that can lapse.

**Not verified, so Phase 2 tests it.** That the stream arrives unbuffered through Vercel; a normal Python cold start time; that the base dependency set installs from the uv lockfile without the `live` group. Vercel's terms also reserve the right to remove Hobby projects and to close accounts "inactive for an extended period"; pushing to the repository counts as activity, but a demo left untouched for a year carries that risk.

**Consequence.** No Dockerfile is needed. The app stays a plain ASGI application so it runs unchanged under Uvicorn locally and on Fly.io if this record is ever replaced. Revisit if Phase 2 fails, or if the owner wants durable hosted runs.

**What Phase 2 found, 2026-11-18.** Measured on the deployed skeleton (`docs/PLAN.md`, Phase 2 log):

- The event stream arrives event by event through Vercel: six events two seconds apart reached the client two seconds apart. Not buffered.
- A cold start, after 18.5 minutes with no traffic, took 1.57 s to the first byte against about 0.4 s warm. One measurement, with a nearly empty app.
- The build installs from `uv.lock` without the `dev` or `live` groups: 28 packages on the host, no `anthropic`. Observed, not configured here.
- A SQLite file in the scratch folder can be created and read back.
- Python 3.14.10, region `iad1`.

The decision stands and the fallback is not needed. Two things this record did not anticipate: a project created from the command line needs its framework named in `vercel.json`, or it deploys nothing; and connecting a project to a private repository needs the owner to give Vercel's GitHub app access to it.

