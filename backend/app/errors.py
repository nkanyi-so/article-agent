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
    # Set when the error came from a model call that was billed although its response
    # could not be used, so the run and the spend ledger can still count it.
    cost_usd: float | None = None

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


class NoCheckableFacts(Refusal):
    """The extract stage found nothing in the transcript that an article could report."""

    code = "no_checkable_facts"
    message = "The transcript contains nothing checkable to report."


class DetailedError(AppError):
    """An error with one short detail for the server's log and the trace: a model id, a
    category, a key prefix. Never upstream text, and never part of the client message."""

    def __init__(self, detail: str = "") -> None:
        super().__init__()
        self.detail = detail


class FixtureMiss(DetailedError):
    """Demo mode, tests and CI were asked for a model response that was never recorded."""

    code = "fixture_miss"
    message = "No recorded response exists for this request."


class ModelRefused(DetailedError):
    """The model declined the request (HTTP 200 with a refusal stop reason)."""

    code = "model_refused"
    http_status = 502
    message = "The model declined this request."


class ModelTruncated(AppError):
    code = "model_truncated"
    http_status = 502
    message = "The model's response was cut off before it finished."


class ModelMismatch(DetailedError):
    """The response came from a model other than the one requested."""

    code = "model_mismatch"
    http_status = 502
    message = "The response came from a different model than the one requested."


class ModelOutputInvalid(DetailedError):
    """The model's output did not have the shape or the references the stage requires."""

    code = "model_output_invalid"
    http_status = 502
    message = "The model's output could not be used."


class ModelCallFailed(DetailedError):
    """The call itself failed: a timeout, a connection error or an API error status."""

    code = "model_call_failed"
    http_status = 502
    retryable = True
    message = "The model could not be reached."


class MissingKey(AppError):
    code = "missing_key"
    http_status = 503
    message = "Live mode needs ANTHROPIC_API_KEY, and it is not set."


class RunTimedOut(AppError):
    code = "run_timeout"
    http_status = 504
    retryable = True
    message = "The run took longer than its time limit."
