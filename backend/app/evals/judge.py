from __future__ import annotations

from app.clients import ClaudeClient
from app.evals.schemas import AngleSupportJudgeOutput, GroundednessJudgeOutput
from app.schemas import Source


class JudgeClient:
    """Wraps ClaudeClient.parse() with the two eval judge prompts."""

    def __init__(self, claude: ClaudeClient) -> None:
        self._claude = claude

    async def judge_groundedness(
        self,
        claims: list[dict],  # [{index, text, cited_source_ids}]
        sources_by_id: dict[str, Source],
    ) -> GroundednessJudgeOutput:
        source_block = "\n".join(
            f"[{sid}] {s.title or 'Untitled'} — {s.snippet or '(no excerpt)'}"
            for sid, s in sources_by_id.items()
        )
        claims_block = "\n".join(
            f'{c["index"]}. "{c["text"]}"  (cites: {c["cited_source_ids"]})'
            for c in claims
        )
        prompt = f"""You are a strict fact-checking judge. You are given an article's \
factual CLAIMS and the SOURCES each claim cites.

Decide, for EACH claim, whether the cited sources' snippets actually support the claim.

Rules:
- Judge ONLY against the provided source snippets. Do NOT use outside knowledge.
- A claim is "supported" only if at least one cited snippet directly states or strongly \
implies it. Plausible-but-unstated = NOT supported.
- supporting_source_ids MUST be a subset of that claim's cited_source_ids.
- If a snippet is too short or vague to verify the claim, mark it NOT supported.
- Be strict: assume nothing beyond what is written.

SOURCES:
{source_block}

CLAIMS:
{claims_block}

Return a judgement per claim (matching claim_index exactly) plus overall_reasoning."""

        result: GroundednessJudgeOutput = await self._claude.parse(  # type: ignore[assignment]
            messages=[{"role": "user", "content": prompt}],
            output_format=GroundednessJudgeOutput,
            max_tokens=4096,
        )
        return result

    async def judge_angle_support(
        self,
        headline: str,
        angle: str,
        rationale: str,
        supporting_sources: list[Source],
    ) -> AngleSupportJudgeOutput:
        source_block = "\n".join(
            f"[{s.id}] {s.title or 'Untitled'} — {s.snippet or '(no excerpt)'}"
            for s in supporting_sources
        )
        prompt = f"""You are an editorial fact-checker. Given a chosen ANGLE for an \
article and the SOURCE snippets cited as supporting it, decide whether the evidence \
genuinely backs the angle.

Rules:
- Judge ONLY against the provided snippets; no outside knowledge.
- "supported" = the snippets contain facts that make this angle accurate and timely.
- A vague or aspirational angle with no concrete supporting fact = NOT supported.
- score: 0.0 (no support) .. 1.0 (fully evidenced).
- supporting_source_ids MUST be a subset of the provided source IDs.
- If snippets are too short to verify the angle, say so and lower your score.

ANGLE
headline: {headline}
angle: {angle}
rationale: {rationale}

SUPPORTING SOURCES:
{source_block}"""

        result: AngleSupportJudgeOutput = await self._claude.parse(  # type: ignore[assignment]
            messages=[{"role": "user", "content": prompt}],
            output_format=AngleSupportJudgeOutput,
            max_tokens=2048,
        )
        return result
