"""Turns a raw Messages API response into a `ModelResponse`, or a typed error.

No SDK import: this runs on plain dictionaries, so it is tested against saved responses
and against hand-built ones for the cases a real call rarely produces.

A response that cannot be used was still billed. Every typed error raised here carries
`cost_usd`, worked out from the response's own usage figures, so the caller can count it.
"""

import json
from typing import Any

from pydantic import ValidationError

from app.errors import AppError, ModelMismatch, ModelOutputInvalid, ModelRefused, ModelTruncated
from app.model.pricing import cost_usd
from app.model.types import ModelRequest, ModelResponse, Usage
from app.schemas import Citation, DraftBlock

# The only ways a response we can use ends. Anything else (a refusal, a cut-off, a pause,
# a tool call, a reason added later) is an error, never quietly treated as success.
NORMAL_STOPS = {"end_turn", "stop_sequence"}


def billed_usd(raw: dict[str, Any], request: ModelRequest) -> float | None:
    """What the call cost, from the raw usage figures, or None if they cannot be read.

    Priced at the requested model's rates: it is what was asked for, and a response from
    another model is an error whose exact price is not in the table.
    """
    try:
        usage = raw["usage"]
        tokens_in = (
            usage["input_tokens"]
            + (usage.get("cache_creation_input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
        )
        return round(cost_usd(request.model, tokens_in, usage["output_tokens"]), 6)
    except KeyError, TypeError:
        return None


def _billed(error: AppError, cost: float | None) -> AppError:
    error.cost_usd = cost
    return error


def response_from_api(
    raw: dict[str, Any],
    request: ModelRequest,
    latency_ms: int,
    attempts: int,
    request_id: str | None = None,
) -> ModelResponse:
    cost = billed_usd(raw, request)
    stop_reason = raw.get("stop_reason")
    if stop_reason == "refusal":
        # Only the category leaves this function. The explanation is upstream text.
        details = raw.get("stop_details") or {}
        raise _billed(ModelRefused(str(details.get("category") or "unspecified")), cost)
    if stop_reason == "max_tokens":
        raise _billed(ModelTruncated(), cost)
    if stop_reason not in NORMAL_STOPS:
        raise _billed(ModelOutputInvalid(f"stop reason {stop_reason!r}"[:60]), cost)
    served = str(raw.get("model"))
    if served != request.model:
        # No silent substitution: a run whose writer changed would make the eval table untrue.
        raise _billed(ModelMismatch(served[:60]), cost)

    try:
        blocks = [
            DraftBlock(
                text=block["text"],
                citations=[
                    Citation(
                        start_segment=citation["start_block_index"],
                        end_segment=citation["end_block_index"],
                        cited_text=citation["cited_text"],
                    )
                    for citation in block.get("citations") or []
                    if citation.get("type") == "content_block_location"
                ],
            )
            for block in raw["content"]
            if block.get("type") == "text"
        ]
        usage = raw["usage"]
        tokens_in = (
            usage["input_tokens"]
            + (usage.get("cache_creation_input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
        )
        details = usage.get("output_tokens_details") or {}
        counted = Usage(
            input_tokens=tokens_in,
            output_tokens=usage["output_tokens"],
            thinking_tokens=details.get("thinking_tokens") or 0,
        )
    except (KeyError, TypeError, AttributeError, ValidationError) as error:
        # A shape the API does not document. Say so with a typed error, not a crash.
        raise _billed(ModelOutputInvalid("response has an unexpected shape"), cost) from error

    parsed: dict[str, Any] | None = None
    if request.output_schema is not None:
        try:
            parsed = json.loads("".join(block.text for block in blocks))
        except json.JSONDecodeError as error:
            raise _billed(ModelOutputInvalid("structured output is not JSON"), cost) from error
        if not isinstance(parsed, dict):
            raise _billed(ModelOutputInvalid("structured output is not an object"), cost)

    return ModelResponse(
        blocks=blocks,
        parsed=parsed,
        stop_reason=str(stop_reason),
        model=served,
        usage=counted,
        cost_usd=round(cost_usd(served, counted.input_tokens, counted.output_tokens), 6),
        latency_ms=latency_ms,
        attempts=attempts,
        request_id=request_id,
    )
