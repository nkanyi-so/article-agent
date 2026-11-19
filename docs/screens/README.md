# The screen, state by state

Taken by `scripts/screenshots.sh` from a production build of the frontend against the backend in demo mode. Each state is in light and dark, at desktop width (1440px) and phone width (390px): `<state>-<theme>-<width>.png`.

| File | What it shows |
|---|---|
| `01-entry` | The first page: the claim, the line saying the demo replays recordings, the three transcripts, and the paste box shown but disabled. |
| `02-live-stages` | A run in progress: the five stages arriving over the event stream. |
| `03-run` | A finished run as it opens: the scores, the article, and the empty panel inviting a choice. |
| `03-run-whole-page` | The same page in full: the article, the list flagged by the judge, the list removed by code, the trace. |
| `04-sentence-with-question` | A sentence chosen: the line it cites, the question that line answered (marked as added by code, not evidence), and the judge's verdict. |
| `05-sentence-flagged` | A sentence the judge flagged, chosen: its cited line and the judge's reason. It stays in the article. |
| `06-headline-flagged` | The headline chosen: why a headline cites no lines, and the judge's reason for flagging this one. |
| `07-trace-stage-open` | The whole page with one stage of the trace opened to show its input and output. |
| `08-rerun-from-draft` | A re-run from the draft stage in progress: two stages copied, one running, two waiting. |
| `09-missing-run` | An address with no run behind it. |

The run shown is the seeded Sallowfield Dental transcript. It is the one seeded run with sentences flagged by the judge and a sentence removed by code; see the Phase 7 log in `docs/PLAN.md` for how it was chosen.
