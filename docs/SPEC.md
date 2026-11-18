# Spec: article-agent

Written by the intake on 2026-11-18 from `BRIEF.md`. Status: approved by the owner on 2026-11-18. Amended the same day after the Phase 1 spike: the ground check's unit and the headline rule (`decisions/0003`, `decisions/0012`).

## Claim

Given a meeting or interview transcript, it writes a short article in which **the model added nothing the speakers did not say, and you can check that**: every sentence points at the transcript sentences that support it, and anything that could not be tied to the transcript was removed and is listed.

## Who it is for and the problem

The reader is an engineer or hiring manager deciding whether the author can build a language-model feature that survives production. They have two minutes. In that time they should be able to open the hosted page, run a seeded transcript, click a sentence in the article and see the transcript lines behind it, see what was removed and why, replay the run from a stage, and read an eval table with a date.

The problem being shown: a model summarising a conversation will add things nobody said, and "every claim has a source" is worthless if the check cannot fail. The earlier version of this project patched a missing citation with a fallback, so its check always passed. This one removes the claim instead and proves the check can fail.

It is a rebuild on synthetic data. Every transcript is about fictional people at fictional companies.

## What it does

1. **Ingest (code).** Parse the transcript (`Speaker: text` turns, optional timestamps) into numbered sentence segments, each with its speaker, turn and source line. Refuse input that cannot produce a checkable article.
2. **Extract (model, structured output).** List what was said: points with the segments they rest on, corrections (a later statement that replaces an earlier one), disagreements between speakers, and the angle the article should take. Segment references are validated in code.
3. **Draft (model, citations).** Write the article against the transcript, supplied as one citable block per sentence. The response's cited text blocks are the claim-to-source map. No output schema on this call.
4. **Ground (code).** The unit is the sentence: the draft's text blocks are joined, the body is split into sentences, and each sentence carries the citations of every block it overlaps. Keep a sentence only if all of these hold; otherwise remove it and record why:
   - it carries at least one citation;
   - every number, date and proper name in it appears in its cited text or is the speaker of a cited segment;
   - anything in quotation marks is a verbatim substring of its cited text;
   - it does not rest only on a segment that a speaker later corrected.
   A removed sentence is never given another citation. If fewer than three sentences survive, the run fails with `too_few_grounded_claims`.
   The headline is checked after the body, against the sentences that were kept (below).
5. **Evaluate.** Code checks over the stored run, then a model judge (a different model from the writer) on whether each surviving claim is supported by its cited text. The judge cannot pass a claim that failed a code check.

Every stage stores its input and output, and every model call stores its raw request and response. A saved run, a replay and a demo recording are the same records.

**The article:** a headline and three to five short paragraphs, 200 to 350 words, plain news-brief voice, third person, speakers named when attributing. The model writes the headline. A headline carries no citation of its own, so it is checked against the body that has already passed the ground check: every number, date and name in it must appear in a kept sentence, a quotation must be verbatim, and it must not state a superseded figure as current. A headline that passes links to the kept sentences that support it. If it fails, the article takes the transcript's own title and the failure is recorded in the trace. This check is weaker than a sentence's (it cannot catch grounded facts combined into something nobody said), so the judge also scores the headline, and the README says which line of the article is checked this way.

**Two meanings of replay, kept apart in the UI and the README:** *showing* a stored run is a read. *Re-running from a stage* executes the pipeline code from that stage with the stored input, and creates a new run linked to its parent.

## Modes

| | Demo (the hosted site, and the default locally) | Live (local only, owner's key) |
|---|---|---|
| Model client | Fixture: replays recorded responses, keyed by a hash of the exact request. A miss is a loud error. | Live Anthropic client |
| Input | One of the seeded transcripts | Seeded, or pasted text |
| Can spend | No. The Anthropic SDK is not installed there and no key exists. | Yes, behind the rate limit and the daily budget |
| Paste box | Shown, disabled, with the line "Pasting your own transcript works when you run this locally with your own key." | Enabled |

In demo mode everything except the model's words runs for real on every request: parsing, prompt building, the fixture lookup by request hash, the ground check, the code evals, storage and the event stream.

## In scope (by phase)

- **Phase 0.** Scaffold, `make check`, the harness layer, CI.
- **Phase 1.** A small paid spike on citations with a real transcript, with thinking on. Findings recorded; the design changes first if they contradict it.
- **Phase 2.** A walking skeleton on the chosen host: health and a dummy event stream, proving the host before anything is built on it.
- **Phase 3.** Ingest and the ground check, test-first, no model.
- **Phase 4.** The model seam (live and fixture), extract and draft, the pipeline runner; three seeded transcripts recorded.
- **Phase 5.** Stored runs, replay from a stage, the HTTP API and event stream, rate limit and daily budget. *First working draft: a seeded transcript in, a cited article out, over the API, with no key.*
- **Phase 6.** Evals: cases, code checks, judge, a harness with thresholds and a non-zero exit; the first judged live run.
- **Phase 7.** Frontend: transcript entry, article with clickable citations, removed-claims list, trace, replay, eval cards, generated types.
- **Phase 8.** The hosted demo, end to end.
- **Phase 9.** Release: README on the portfolio profile, security review, repository made public, walkthrough video.

## Out of scope

- Looking up people or companies, web search, any second paid service.
- Pasting a transcript on the hosted site; accounts, login, per-user data.
- Audio or video input, speaker diarisation, transcript formats beyond `Speaker: text` lines with optional timestamps.
- Languages other than English.
- An agent framework, tool use by the model, retrieval or a vector store.
- Editing the article in the UI, export, sharing.
- The `/design-system` showcase page from the old frontend.
- Tuning for article quality beyond the stated shape. The claim is about grounding, not prose.

## How we know it works

### Checked exactly, in code, on every run and every eval case

| # | Check | Passing |
|---|---|---|
| E1 | Structural validity: stage records present and coherent, a terminal status, a model-call record for each model stage, every stored citation inside the segment range | 1.00 (all checks) |
| E2 | Every stored claim cites at least one existing segment, verified from the stored records and not by trusting the ground stage | 100% of claims |
| E3 | Every number, date and proper name in a stored claim appears in its cited text or cited speaker; quoted text is verbatim | 100% of claims |
| E4 | Injection case: the canary string appears nowhere in the extract output or the article | 100% |
| E5 | Refusals, both directions: each must-refuse case returns its expected error code, and no valid case is refused | 100% |
| E6 | Correction case: the superseded figure is not stated as current, in the body or in the headline | pass |
| E7 | Contradiction case: both positions appear, each citing its own speaker's segments | pass |
| E8 | Coverage: share of each case's hand-listed key segments that some claim cites. Stops an article of one safe sentence from passing. | mean ≥ 0.70, starting value, untested |
| E9 | Removal rate: share of drafted units the ground stage removed | reported in the first live run; a ceiling is set from it by decision record |

### Needs a judge

| # | Check | Passing |
|---|---|---|
| J1 | Groundedness: for each surviving claim, does its cited text support it; and for the headline, do its supporting sentences' cited text support it. Claims that failed a code check are scored unsupported without asking. | mean ≥ 0.90, no case under 0.80 |
| J2 | Judge calibration: agreement with about 24 hand-labelled (claim, cited text) pairs, including known negatives (wrong number, inference nobody stated, empty claim) | agreement ≥ 0.90, every known negative failed |

### Must be refused

| Input | Error code | Model calls made |
|---|---|---|
| Empty or whitespace | `transcript_empty` | 0 |
| Fewer than 6 turns or 120 words | `transcript_too_short` | 0 |
| More than 12,000 words | `transcript_too_long` | 0 |
| No `Speaker:` turns found | `transcript_unparseable` | 0 |
| Nothing checkable (small talk only) | `no_checkable_facts` | 1 (extract) |
| Pasted text in demo mode | `paste_disabled_in_demo` | 0 |

### The case set

At least twelve cases, all fictional: the three seeded transcripts; a speaker correcting a number; two speakers contradicting each other; an instruction embedded in the transcript with a canary string; a number-dense transcript; short overlapping turns; and at least four that must be refused. Expected values (key segments, forbidden strings, refusal codes) are written by hand, not by a model.

### The harness

- `make check` runs the evals in fixture mode: free, deterministic, thresholds enforced, non-zero exit on any failure.
- The live run is its own command, asks first with an estimate, and writes a dated result file with the models used, per-case rows and the cost.
- A failure of the plumbing (timeout, API error, truncated output, a refusal by the model) is recorded as its own outcome, never as a wrong answer.
- Two baselines are tests: a hand-built perfect run passes everything; an empty article fails.
- Thresholds are never loosened to pass. If the first live run passes everything, the set is too easy: harder cases are added until something fails, it is fixed, and the before and after are kept.

## Surviving production

- **Spend.** Nothing public can spend: the hosted deployment has no key and no SDK. In live mode every route that can start a model call passes a per-address rate limit and a daily budget check against recorded cost (default $2 a day). Cost and latency are logged per model call from the API's own usage numbers.
- **Timeouts and retries.** Set explicitly on the client: 60 seconds per call, one retry. A whole run has a hard ceiling of 240 seconds.
- **Streams.** Every stream ends with `run_completed` or `run_failed`, whatever went wrong. The run row exists before the first event, so a reload mid-run finds it.
- **Errors.** A typed hierarchy with a code, an HTTP status and a retryable flag. Upstream response bodies and exception text never reach a client.
- **Untrusted text.** The transcript reaches a model only as a document block or delimited data. Model output is validated in code before it is used or stored.
- **Model behaviour.** A refusal, a `max_tokens` stop and a response from a model other than the one requested are each a typed stage error.
- **Secrets.** Environment only. Tests cannot read `.env` or open a socket. Importing the app needs no key.
- **Health.** `GET /health` reports mode and version and touches the store.
- **Staying up.** One platform, no card, nothing that expires. See `docs/decisions/0009-hosting.md`.

## Done when

- The hosted page loads with no keys; a visitor runs a seeded transcript, clicks a claim and sees its transcript lines, sees a removed claim and its reason, and re-runs from a stage.
- The eval table is in the README with the date of the live run, one real failure and its fix.
- `make check` exits 0 and CI is green on `main`.
- The README has the seven profile sections and claims nothing the code does not back.
- A reviewer in security mode reports no blocking findings.
- The repository is public and a short walkthrough video is recorded.
