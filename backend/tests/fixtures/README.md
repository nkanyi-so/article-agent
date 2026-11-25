# Test fixtures

Real model responses, saved while the citations API was first measured (`docs/decisions/0012`) and kept here so the tests run on real output. Nothing in this folder is written by hand, and nothing here is read from the network.

- `transcripts/`: the two fictional transcripts those calls used.
- `draft/`: eleven draft responses with citations, one citable block per sentence (seven on transcript 1, four on transcript 2). Each file holds the raw request and the raw response of one call.
- `extract/`: the extract call's structured output for each transcript. Transcript 2's names the correction (segment 4 superseded by segment 16).

The drafts made with one block per turn are not here: their block indexes do not line up with sentence segments.

Hand-altered responses are built inside the tests from these files, so each alteration is visible next to the assertion it supports.
