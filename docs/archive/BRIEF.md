# Brief: article-agent, rebuilt

Written 2026-11-18 at the end of the session that audited the old project. It is for a fresh session that has seen none of that work. Start with `/harness-intake` in this folder, with the `llm-app` and `portfolio-piece` profiles. This brief is input to the intake, not a spec: the intake still owns the spec, the architecture, the plan and the decision records.

Anything marked **verified** was checked on 2026-11-18 against the source given. Anything marked **judgement** is the previous session's opinion. Section 7 lists what was not checked.

---

## 1. What the product is

A public portfolio piece. You give it a transcript of a meeting or interview; it writes a short article in which every factual claim points at the transcript lines that support it. It shows its work: a stage-by-stage trace, saved runs that can be replayed from any stage, and an eval score.

The one claim it has to prove: **the model added nothing the speakers did not say, and you can check that.**

The reader is an engineer or hiring manager deciding whether the author can build a language-model feature that survives production. It is a rebuild on synthetic data: fictional companies, fictional people, no client material.

Where it should end up (the owner's six targets, unchanged from the old project):

1. A working transcript entry point. This is the core.
2. Runs saved to a database, with replay from any stage.
3. A real eval run, with numbers and a date, in the README.
4. Three seeded transcripts about fictional companies, so the hosted demo works with no keys on the visitor's side.
5. Deployed.
6. A README on the portfolio-piece profile (seven sections), with nothing claimed that the code does not back.

## 2. What happened before, and what the audit proved

The old project (June 2026) built the *other* entry point: type a person's name or LinkedIn URL, look them up through two paid data services, pull recent news, and draft an article about them. The transcript tab was a "coming soon" placeholder with no backend. It was audited on 2026-11-18 by an agent that ran the code. The findings that matter for a rebuild:

- **It was public and deployed with no spend guard.** No auth, rate limit or budget cap on four routes that each triggered several paid model calls plus paid lookups. The run list returned every visitor's runs, including a looked-up person's email when the data service supplied one. Its own docs said it had never been deployed.
- **"Every claim is sourced" could not fail.** When the model cited a source that did not exist, the draft stage stripped the bad ID and then gave the claim the angle's sources instead. So every claim always had a citation on paper, and the structural eval could never catch an unsupported one.
- **There was no real eval result.** The committed "mock judge" run used no judge; it skipped both judged evals. The harness had no pass thresholds and exited 0 when every row failed. The judge was the same model as the writer.
- **No model seam.** One concrete live client, no interface, no fixture implementation; every run needed three API keys before the first stage ran; the settings module loaded the real `.env` at import, including under pytest. Tests were safe only because each one mocked by hand.
- **Fixtures and samples were about real, named executives, with invented news,** in a public git history. This is the reason there is no history here.
- **Unbacked claims in the README and agent file:** a vector store and an embeddings service that were never built, a "ground and fact-check" stage that did not exist.
- **Errors leaked and streams hung.** Upstream errors that were not the pipeline's own type ended the event stream with no terminal event, and the UI stayed on "streaming" forever. Upstream response bodies and exception text were returned to clients.
- **What was sound:** the typed error hierarchy, the stage envelope (status, timing, sources, output, error per stage), the event stream, the eval layer's shape (code checks wrapped around a model judge, so the judge cannot lift a claim that failed a code check), and the frontend shell.

**Why rebuild rather than fix.** Most backend code worth keeping served the name-lookup path, which was already going to be hidden from the public demo. The orchestrator, the clients and the schemas all needed restructuring for replay, a model seam and transcript input. And patching could not remove the real-person fixtures from a public history. The old repository is now private, renamed `article-agent-legacy`, and holds the full audit (`docs/AUDIT.md` on branch `chore/harness-adopt`).

**Lessons to carry as rules from day one** (judgement, each from a finding above):

- A claim without a valid citation is removed and recorded. It is never patched with a fallback.
- The model sits behind one interface with a live and a fixture implementation. Tests, CI and the demo can only build the fixture one.
- Tests cannot read `.env` or open a socket.
- No real people or companies anywhere, including sample data in UI placeholders.
- Nothing public can spend. If a route can cause a paid call, it has a rate limit and a daily cap, or it does not exist on the hosted site.
- An eval harness has thresholds and a non-zero exit, and its default mode costs nothing.
- Every stream ends with a terminal event, whatever went wrong.

## 3. What is in this folder

| Path | What | State |
|---|---|---|
| `frontend/` | The old Next.js app: shell, sidebar, theme, run page with article view and trace view, eval cards, primitives, typed API client and event-stream parser. 4,203 lines in `src/`. | Kept as working code. See the caveats below. |
| `design/` | Static design reference for the UI (`Bylined.dc.html`). | Reference only. Its mock data uses placeholder names. |
| `reference/legacy-backend/` | The old eval layer, the error types and four eval test files. | **To read, not to run.** See `reference/README.md`. |
| `BRIEF.md` | This file. | |
| `.gitignore` | Ignores `.env`, build output, local databases. | |

There is no git repository here yet. The intake runs `git init` and sets the remote. The GitHub name `article-agent` is free again under the owner's account.

### Frontend caveats (verified by running the checks in this folder; results in section 8)

- **Sample data was changed.** A real name and company in `src/app/design-system/page.tsx` and in the placeholders of `src/components/new-article/InputForm.tsx` were replaced with a fictional person and company. No other source change was made.
- **It still contains the name-lookup UI.** To delete or rewrite: `components/new-article/DisambiguationChooser.tsx`, the name and LinkedIn half of `InputForm.tsx`, the "Resolve identity" stage labels in `components/run/ProcessingView.tsx` and `StageItem.tsx`, the person-name logic in `app/page.tsx`, `components/run/RunHeader.tsx` and `components/shell/Sidebar.tsx`, and the person shapes in `lib/run-types.ts`. Vendor names for the dropped data services appear in those files.
- **The transcript tab is a static placeholder** (`InputForm.tsx`, the "coming soon" panel).
- **Types are hand-copied** (`lib/run-types.ts`, `lib/stream-types.ts`) from a backend that no longer exists. Replace with generated types (section 5.5).
- **Known defects from the audit:** if the stream closes without a terminal event no handler fires (`lib/api.ts`); the run page shows every error as "not found" (`app/runs/[id]/page.tsx`); the URL is rewritten to the run page before the run is stored, so a reload mid-run gets a 404 (`app/page.tsx`); a checkbox lets any visitor ask for the paid judged evals (`InputForm.tsx`).
- **No tests** and no test runner.
- **Styling is inline styles over CSS variables.** Tailwind 4 is installed and unused.
- **Next.js 16.2.9.** `frontend/AGENTS.md` carries a real rule: this version differs from what most references describe, so read the guide bundled under `node_modules/next/dist/docs/` before writing frontend code. Latest stable is 16.4.6 (verified, npm registry).

### Left behind, and why

| Left behind | Why |
|---|---|
| All backend runtime code: orchestrator, clients, schemas, the four stages, settings | Built around the person lookup; needed restructuring anyway; simpler to write test-first against the new design. |
| The person-lookup stages, their eval (`entity_resolution`) and their tests | The path is dropped (section 5.6). |
| `tests/fixtures/*.json`, `evals/samples.py`, `conftest.py` | Real people, invented news, real news-site URLs. |
| The other eight test files | They test the old pipeline shape through hand-rolled mocks. The cases are worth re-deriving; the code is not. |
| `evals/harness.py` | No thresholds, always exit 0, paid by default. |
| `Dockerfile`, two conflicting `railway.json` files, `DEPLOY.md` | Described a deployment that no longer matches anything. The container ran as root and shipped the test runner. |
| `README.md`, the old `CLAUDE.md`, the June status and architecture docs | Contained claims the code did not back. |
| `docs/AUDIT.md`, the draft spec and plan | They name the real people from the fixtures, so they stay in the private legacy repo. Their substance is in this brief. |
| `frontend/README.md` | Framework boilerplate, not about this project. |
| `.env`, `frontend/.env.local`, `node_modules`, git history, the harness layer | Secrets, build output, history, and a layer the intake installs fresh. |

## 4. Shape the owner proposed

A straight pipeline, no agent framework. Roughly: ingest the transcript into numbered segments (code) → extract what was said (model) → pick an angle (model) → draft with citations (model) → ground check (code) → evals. Every stage saves its input and output; a saved run, a replay and a recorded demo run are the same records. Writer and judge are different models. Frontend types are generated from the backend schema. No name lookup. The hosted demo replays recorded runs only.

The intake decides the actual stage list. Section 5 is what checking those ideas found.

## 5. Design ideas, checked

### 5.1 Anthropic's citations feature for the draft: **use it, but not the way it was proposed**

Source for everything in this subsection unless noted: https://platform.claude.com/docs/en/build-with-claude/citations (verified).

- **How it works.** Citations are enabled per `document` content block with `"citations": {"enabled": true}`; all documents in a request have it on, or none. Three document types: plain text (the API chunks it into sentences, citations carry character indices), PDF (sentences, page numbers), and **custom content** (you supply the blocks, "The API does no further chunking: each text block that you provide is one chunk, the smallest unit that Claude can cite"). The docs name transcripts as a use for custom content.
- **What comes back.** The answer is a list of text blocks; a block that makes a cited statement carries `citations`, each `{"type": "content_block_location", "cited_text", "document_index", "document_title", "start_block_index", "end_block_index"}` for custom content (end index exclusive), or `char_location` with `start_char_index` / `end_char_index` for plain text.
- **The guarantee.** "Because the API parses citations into the response formats … and extracts `cited_text` directly, citations are guaranteed to contain valid pointers to the provided documents." So a cited span is always a real range of the transcript. This replaces the old project's weakest point (model-written source IDs that had to be stripped and patched).
- **What is not guaranteed.** Coverage. The docs say of structured data "Check that each field has a value and at least one citation. The API doesn't guarantee either." Uncited text blocks can appear. Nor does a valid pointer mean the span *supports* the claim. So the code check on top is still needed, and so is the judge.
- **Granularity is yours to choose.** With custom content a citation cannot point inside a block. One block per speaker turn gives turn-level citations; for tighter spans, split turns into sentence blocks yourself and keep a map from block index to speaker and line. This is a real design decision (section 6, Q3).
- **Cost.** "Enabling citations incurs a slight increase in input tokens because of system prompt additions and document chunking." "The `cited_text` field … does not count toward output tokens", and is not counted as input when passed back in later turns. No separate price line for citations on the pricing page (https://platform.claude.com/docs/en/about-claude/pricing).
- **Models.** "All active models support citations."
- **Works with:** prompt caching (cache the document block), token counting, batch, streaming (`citations_delta`).
- **Where the proposal was wrong: citations do not combine with structured output.** "Citations cannot be used together with structured outputs. If you enable citations on any user-provided document … and also include the `output_config.format` parameter (or the deprecated `output_format` parameter), the API returns a 400 error." The structured-outputs page says the same (https://platform.claude.com/docs/en/build-with-claude/structured-outputs). The old backend used `messages.parse` with a Pydantic model for every model call, so the draft stage cannot be a port.

**Conclusion (judgement).** The draft call is a citations call with no output schema. The model writes the article as prose; the response's text blocks, with their citations, *are* the claim-to-source map. Code then turns blocks into claims and enforces: every factual sentence carries at least one citation, or it is removed and recorded; every number, date and proper name in a claim appears in its `cited_text`. Stages that need a schema (extract, angle, the judge's verdict) use structured outputs in separate calls with no citation-enabled documents. The docs' own advice for per-field citations is to prompt for one line per field and to avoid asking for JSON only, which "might contain few or no citations".

**Not stated in the docs, so test it in a first small paid spike before designing around it:** whether citations combine with thinking (which cannot be turned off on some current models, see 5.4) and with tool use.

### 5.2 Every stage saves its input and output, so saved runs and replay are one mechanism: **agreed, with two additions** (judgement)

- The audit supports it: the old run object already carried each stage's envelope, and replay was missing only because the stages were inline in one generator and nothing was persisted.
- Three uses fall out of one table of stage records: showing a saved run, re-executing from stage N with the stored input of N, and the hosted demo's recordings.
- **Addition 1.** Store the raw model request and response per call (including the citation blocks), not just the parsed stage output. The fixture client replays those; without them a "replay" in the demo cannot re-run the code after the model call.
- **Addition 2.** Key each recording by a hash of the prompt, model and schema, and fail loudly on a miss. Any prompt edit then invalidates the recording visibly instead of replaying a stale answer.
- **Be precise in the UI and README about two meanings of replay:** re-showing a stored run (a read) versus re-executing from a stage (runs code, and in live mode spends).
- **Storage.** SQLite is enough. The FastAPI tutorial shows SQLModel with a sync engine and plain `def` routes (https://fastapi.tiangolo.com/tutorial/sql-databases/, verified, last fifth of the page unread). Every "async" SQLite option is a thread underneath: SQLAlchemy's docs say of `aiosqlite`, "It does not actually use non-blocking IO" (https://docs.sqlalchemy.org/en/20/dialects/sqlite.html, verified). The least machinery is the standard library's `sqlite3` in a thread, or `aiosqlite` directly.

### 5.3 No agent framework: **agreed** (verified against Anthropic's guidance)

Source: https://www.anthropic.com/engineering/building-effective-agents. "Workflows are systems where LLMs and tools are orchestrated through predefined code paths", as opposed to agents, where "LLMs dynamically direct their own processes and tool usage". "We recommend finding the simplest solution possible, and only increasing complexity when needed." On frameworks: "they often create extra layers of abstraction that can obscure the underlying prompts". This product is prompt chaining ("each LLM call processes the output of the previous one") followed by an evaluator. A plain function per stage also makes per-stage input and output trivial to save, which 5.2 depends on.

### 5.4 Writer and judge are different models: **agreed; the model IDs are confirmed; the official backing is thinner than assumed**

- **Current model IDs and list prices per million tokens, input / output** (verified, https://platform.claude.com/docs/en/models/overview and the pricing page): `claude-fable-5-2` $8 / $40; `claude-opus-5-5` $4 / $20; `claude-sonnet-5-5` $2 / $10; `claude-haiku-5-5` $0.10 / $0.50 for prompts up to 100k tokens. "Every Claude model ID is a pinned snapshot, including the dateless IDs", so there is no separate alias to pin.
- The old code's `claude-opus-4-8` is still active, "Not sooner than May 28, 2027" (https://platform.claude.com/docs/en/about-claude/model-deprecations), at $5 / $25. There is no reason to keep it.
- Anthropic's general advice: "If you're unsure which model to use, start with Claude Opus 5.5 for most workloads." The docs give no specific recommendation for a writing model or a judge model.
- **On the different-judge rule.** The only official statement found is a code comment in the eval guide: "Generally best practice to evaluate with a different model from the one used to generate the evaluated output" (https://platform.claude.com/docs/en/test-and-evaluate/develop-tests). The examples on that page use the same model for both. So it is good practice, not a documented requirement; say so in the decision record rather than citing it as a rule.
- **Judgement:** a different Claude model reduces self-grading but does not make the judge independent. The stronger protection is the one the old eval layer already had: code checks the judge cannot override. Starting proposal: writer `claude-sonnet-5-5`, judge `claude-opus-5-5`; let the first eval run decide.
- **Things that changed since June and will bite a port** (verified, Python SDK and structured-outputs pages):
  - The Python SDK is at 2.10.0 (https://pypi.org/project/anthropic/); the old code pinned 0.109.1.
  - "`temperature`, `top_p`, `top_k` | Removed in API version `2026-10-21` | Returns a 400 error." A judge cannot be pinned with `temperature=0`. Determinism for tests comes from the fixture client, not from sampling settings.
  - Thinking is "Adaptive (always on)" on Opus 5.5 and Fable 5.2 and cannot be turned off. This is why the citations-with-thinking question in 5.1 needs a spike.
  - SDK defaults: "By default requests time out after 10 minutes", and it "retries certain errors twice" (connection errors, 408, 409, 429, 5xx). Set both explicitly; a 120-second timeout with default retries can mean three attempts. There is an `AsyncAnthropic` client, so the old sync-SDK-in-a-thread pattern is unnecessary.
  - Structured outputs are stable; the API parameter is `output_config.format`. `client.messages.parse(output_format=PydanticModel)` is still the recommended Python helper. Unsupported in schemas: numeric and string length constraints, recursive schemas, among others; refusals and `max_tokens` stops can return output that does not match the schema.

### 5.5 Frontend types generated from the backend schema: **agreed and shown to work, with one gap**

Sources: https://openapi-ts.dev/cli, https://fastapi.tiangolo.com/tutorial/server-sent-events/, FastAPI release notes; plus a scratch experiment run on 2026-11-18 with FastAPI 0.164.0, Pydantic 2.14.3 and `openapi-typescript` 7.13.0. Items marked *experiment* come from that run, not from documentation.

- FastAPI has first-class server-sent events since 0.135.0: `EventSourceResponse` from `fastapi.sse`, and "If you declare the return type as `AsyncIterable[Item]`, FastAPI will use it to validate, document, and serialize the data using Pydantic." (verified)
- *Experiment:* declare the event type as a **named** discriminated union (a `type` alias or a `RootModel`) and it appears in the schema as one named component; an unnamed union is inlined. A route that yields the generic `ServerSentEvent` envelope documents only `data: string` and loses the payload types.
- `app.openapi()` returns the schema with no server running (verified as an API; using it as an offline dump is *experiment*, not a documented recipe). Importing the app must therefore not require keys.
- `openapi-typescript` turns OpenAPI 3.0 and 3.1 into one types-only file and has `--check`, "Check that the generated types are up-to-date" (verified). *Experiment:* exit 1 when stale; Pydantic's discriminated unions become proper TypeScript unions with a required literal tag; `str | None` becomes `string | null`.
- **The gap** (*experiment*): the stream response itself is typed `"text/event-stream": unknown`, because FastAPI describes it with the newer `itemSchema` keyword, which this version of the generator ignores. The event union is still generated under `components["schemas"]`; the frontend imports it from there. The `JSON.parse(event.data)` cast is unchecked at runtime in every option.
- Alternatives looked at: `@hey-api/openapi-ts` (the generator the FastAPI docs name; pre-1.0, generates a whole client, needs a newer Node than this machine has, not run); `pydantic-to-typescript` (dormant since 2024); generating from Pydantic's JSON Schema with `json-schema-to-typescript` (*experiment:* weaker output, the tag came out optional).

**Conclusion (judgement).** Typed stream route on the backend, a script that writes `openapi.json`, `openapi-typescript` to one file in the frontend, and `--check` in `make check` so drift fails the gate. This removes the hand-copy rule from the old project entirely.

Also verified while checking: FastAPI 0.164.0 requires Python 3.11 or later (3.10 was dropped on 2026-11-13); Pydantic 2.14.3; Uvicorn 0.54.0; Python 3.13 and 3.14 are supported by both.

### 5.6 Drop the name-lookup path entirely: **agreed** (judgement, from the audit)

It needs two paid services; one of them returned 403 on the owner's plan in June, so every run fell back to a stub. It looks up real people, which the portfolio profile's synthetic-data rule forbids on a public demo. Its eval passed whenever any profile URL appeared in search results, without checking it was the right person. And the product's claim is about transcripts. Dropping it also removes the disambiguation state, a personal-data exposure, and the need for web content in prompts (one less injection surface). Cost: the frontend work listed in section 3.

### 5.7 Hosted demo replays recorded runs only, no live model, no keys: **agreed, and it raises a question the proposal did not ask** (judgement)

- It satisfies the portfolio profile directly: works with no keys on the visitor's side, and has nothing that can spend.
- The old deployment shows the other half of the profile ("still load months later. Prefer nothing that can pause or expire"): its backend host stopped the service about a month after the last deploy, on a trial plan, and the public page then pointed at nothing for four months.
- **The question:** if the hosted demo only replays recordings, does it need a running backend at all? Two honest designs:
  - **A. Backend container in demo mode.** The real pipeline code runs on the server with the fixture client. The claim "this is the real code path" is true on the hosted site. Needs a host that does not stop, which means paying for one or choosing carefully.
  - **B. Static recordings served by the frontend.** Nothing to pause, nothing to pay for. But "replay from any stage" on the hosted site is then playback of stored stage records, and the real pipeline only runs locally (with zero keys, in fixture mode) and in CI.
- Either way the README must say which it is. This is the owner's call (section 6, Q1).

## 6. Open questions for the intake

Only the owner can answer these. Recommended answers are judgement.

- **Q1. Does the hosted demo run a backend (5.7 A) or serve static recordings (5.7 B)?** Recommended: A if the owner will pay for an always-on container host; otherwise B, stated plainly. Do not use a trial plan again.
- **Q2. Can a visitor paste their own transcript on the hosted site?** The earlier draft spec said no: shown but disabled, works locally with the owner's key. The alternative is a live path with a small daily cap, which contradicts "no live model, no keys".
- **Q3. Citation granularity:** one block per speaker turn, or per sentence within a turn? Recommended: per sentence, with speaker and line kept in a side map, so a cited span is tight enough to check numbers and names against.
- **Q4. What should the article be?** Length, voice, whether an "angle" stage is worth a model call or the draft can choose its own. The old angle stage existed to choose among news results, which no longer exist.
- **Q5. Budget for live runs.** At least: one small spike (5.1), one recording run for the three seeded transcripts, one judged eval run, and a second after the first real failure is fixed. Each asks first, with an estimate.
- **Q6. What to do with the old infrastructure** (section 9). In particular, the old backend project still stores five API keys.
- **Q7. Names.** The GitHub name `article-agent` is free. This folder is `article-agent-v2` only because the old local folder still has that name.
- **Q8. Keep the `/design-system` page?** 570 lines, a component showcase. Useful for a portfolio reader or noise.
- **Q9. The eval numbers.** The earlier draft spec proposed: structural validity 1.00; 100% of stored claims cite an existing segment; 100% of numbers, dates and names in a claim appear in its cited text; judged groundedness mean of at least 0.90 with no case under 0.80; at least ten cases including a speaker correcting a number, two speakers contradicting each other, an instruction embedded in the transcript with a canary string, and at least three that must be refused (empty, too short, no checkable facts). These were never tested against a judged run. Per the profile, if the first live run passes everything the set is too easy.

## 7. Not checked

- **No live model call was made.** Nothing about how the current models actually behave with citations on a transcript is known: how often sentences come back uncited, how the model handles a corrected number, what a run costs.
- **Citations with thinking, and citations with tool use:** the docs do not say. Untested.
- Whether the old frontend works in a browser. Only the type check, lint and build were run (section 8); no page was loaded and no flow was clicked through.
- `@hey-api/openapi-ts` and the newest `json-schema-to-typescript` were not run (they need a newer Node than is installed here).
- The type-generation findings marked *experiment* rest on one scratch run, not on documentation.
- Most quotes from documentation pages were relayed by a fetch tool and should be re-read at the source before they are quoted in a decision record. Library versions and model prices are as of 2026-11-18 and will move; principle 6 of the harness (check current docs before planning a phase) still applies.
- Whether the judged-eval thresholds in Q9 are reachable.

## 8. Frontend check results in this folder

Run on 2026-11-18 in `frontend/` with a stripped environment, after the sample-data change:

| Command | Result |
|---|---|
| `npm ci` | exit 0 |
| `npx tsc --noEmit` | exit 0 |
| `npm run lint` | **fails: 3 errors, 1 warning.** `react-hooks/set-state-in-effect` at `components/shell/Sidebar.tsx:16` and `components/shell/ThemeToggle.tsx:16`; `react/no-unescaped-entities` at `app/design-system/page.tsx:322`; an unused disable directive in `components/shell/ThemeScript.tsx`. Same as in the old repo. |
| `npm run build` | exit 0; routes `/`, `/_not-found`, `/design-system` static, `/runs/[id]` dynamic |

So the ported frontend compiles and builds, and Phase 0 has three lint errors to fix or quarantine before `make check` can be green. `node_modules/` from this run is in the folder and is ignored; the build output was deleted.

## 9. State of the old infrastructure (as left on 2026-11-18)

- **GitHub:** the old repository is private and renamed `article-agent-legacy`. The adoption work (audit, draft spec, plan, harness notes, decision record) is on branch `chore/harness-adopt`, pushed, not merged.
- **Frontend host:** the old project is paused; its three public addresses return 503. It is still connected to the legacy repository and would build on a push to `main` there. It can be reused for the rebuild by pointing it at the new repository, or deleted.
- **Backend host:** the old project has one service with no running deployment (every deployment is in a removed or failed state; its public address returns "Application not found"). Nothing was deleted. **It still stores five API keys as variables**, two of them for services that were never used. It is still connected to the legacy repository.
- Nothing in this folder depends on any of it.
