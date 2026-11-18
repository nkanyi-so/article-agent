# 0002: the draft uses the Citations API, one citable block per sentence

**Status:** accepted by the owner on 2026-11-18. Phase 1 confirmed it, with caveats recorded in `0012`.

**Context.** The old project asked the model to write source ids, then stripped the invalid ones. The claim here needs a pointer that cannot be invented. Checked on 2026-11-18 against https://platform.claude.com/docs/en/build-with-claude/citations, read in full:

- Citations are switched on per document block, all documents in a request or none.
- A custom content document is not chunked further: "each text block that you provide is one chunk, the smallest unit that Claude can cite." The page names transcripts as a use for it.
- A citation on custom content is `content_block_location` with `cited_text`, `document_index`, `document_title`, `start_block_index` and `end_block_index`, 0-indexed, end exclusive.
- "citations are guaranteed to contain valid pointers to the provided documents."
- Coverage is not guaranteed: "Check that each field has a value and at least one citation. The API doesn't guarantee either."
- "Citations cannot be used together with structured outputs"; sending both returns a 400.
- `cited_text` "does not count toward output tokens". "All active models support citations."
- The page says nothing about thinking or about tool use. Its examples use a model on which thinking cannot be turned off, so the two evidently coexist, but that is inference.
- No limit on the number of blocks in a custom content document is stated.

**Decision.**

- The transcript goes to the draft call as one custom content document with one text block per sentence. The segment index is the block index.
- The draft call has no output schema. The model writes prose; the response's text blocks and their citations are the claim-to-source map.
- Speaker and line are kept in code beside each segment, and the speaker's name is also the start of each block's text so the model can attribute.
- Stages that need a schema (extract, the judge) are separate calls with no citable document.

**Why per sentence (the owner's answer to Q3).** A citation cannot point inside a block. Per turn, a cited span can be a paragraph long, too loose to check a number or a name against. Per sentence, the span is tight enough for the entity check in `0003`.

**Consequence.** A pointer is always a real range of the transcript, by the API's own guarantee. What is not guaranteed, that each sentence is cited and that the span supports it, is the job of the ground check and the judge. Not known until Phase 1: how often text comes back uncited, how many sentences share one cited block, whether a headline is cited, and what a run costs. If the uncited share is high enough that articles are gutted, this record is rewritten before anything is built on it.
