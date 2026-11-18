"""Typed errors. Each carries a code, an HTTP status and whether a retry can help.

The message of every error here is fixed text written in this file. It never contains
transcript text, model output or an upstream response, so it is safe to show a client.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas import GroundResult


class AppError(Exception):
    code: str = "internal_error"
    http_status: int = 500
    retryable: bool = False
    message: str = "Something went wrong."

    def __init__(self) -> None:
        super().__init__(self.message)


class Refusal(AppError):
    """The input cannot produce a checkable article. Refused in code, before any model call."""

    http_status = 422


class TranscriptEmpty(Refusal):
    code = "transcript_empty"
    message = "The transcript is empty."


class TranscriptUnparseable(Refusal):
    code = "transcript_unparseable"
    message = "No 'Speaker: text' turns were found in the transcript."


class TranscriptTooShort(Refusal):
    code = "transcript_too_short"
    message = "The transcript needs at least 6 turns and 120 words."


class TranscriptTooLong(Refusal):
    code = "transcript_too_long"
    http_status = 413
    message = "The transcript is longer than 12,000 words."


class TooFewGroundedClaims(AppError):
    """Fewer than three sentences of the draft survived the ground check.

    Carries the result, so the trace can still show what was kept and what was removed.
    """

    code = "too_few_grounded_claims"
    http_status = 422
    message = "Too little of the draft could be tied to the transcript to make an article."

    def __init__(self, result: GroundResult) -> None:
        super().__init__()
        self.result = result
