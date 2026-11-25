# 0001: a plain staged pipeline, with the angle folded into extract

**Status:** proposed, 2026-11-18

**Context.** The product is a fixed sequence: parse, find what was said, write, check, score. The old project had a separate "angle" stage whose job was choosing among news results, which no longer exist. Whether an angle stage earns a model call was left open at the start.

**Decision.**

- Five stages as plain async functions called in order by one runner: `ingest` (code), `extract` (model), `draft` (model), `ground` (code), `evaluate` (code, then a model judge). No agent framework, no tool use by the model.
- No separate angle stage. The angle (a headline idea and which points lead) is a field of the extract output.

**Why no framework.** Anthropic's guidance separates workflows, "systems where LLMs and tools are orchestrated through predefined code paths", from agents, and recommends "finding the simplest solution possible, and only increasing complexity when needed" (https://www.anthropic.com/engineering/building-effective-agents, as quoted in the original brief; re-read before quoting in the README). This is prompt chaining followed by an evaluator. A function per stage is also what makes storing each stage's input and output trivial.

**Why the angle does not get its own call.** A separate call would see exactly what extract already has, the list of points, and nothing new. It would add a paid call, latency and a third prompt to keep stable for the recordings, in return for a choice the extract call can make in one extra field. Extract stays, because it does three things the draft cannot: it decides `no_checkable_facts` before the costlier draft call, it names corrections so code can enforce them, and it gives the trace a step a reader can check against the transcript.

**Consequence.** Two model calls to write an article, one to judge it. Re-running from `draft` with a different angle is possible by editing the stored extract output, in live mode. Revisit if the first live eval shows articles that are grounded but miss the point of the conversation (coverage, E8): that would be the evidence an angle step is worth its call.
