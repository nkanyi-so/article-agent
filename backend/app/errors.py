from __future__ import annotations


class PipelineError(Exception):
    """Base for all pipeline errors that produce a clean HTTP response.

    Sub-classes set class-level defaults; callers may override via kwargs.
    """

    code: str = "pipeline_error"
    http_status: int = 500
    retryable: bool = False

    def __init__(self, message: str, *, retryable: bool | None = None) -> None:
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable


class MissingKeyError(PipelineError):
    """An environment variable / API key is absent."""

    code = "missing_key"
    http_status = 503

    def __init__(self, key_name: str) -> None:
        super().__init__(
            f"Required environment variable '{key_name}' is not set. "
            "Add it to your .env file or Railway environment variables."
        )
        self.key_name = key_name


class EnrichNotFoundError(PipelineError):
    """Apollo found no match for this person."""

    code = "apollo_not_found"
    http_status = 404


class EmptyResearchError(PipelineError):
    """Exa returned no news — cannot ground an angle."""

    code = "exa_empty"
    http_status = 422
    retryable = True


class ClaudeError(PipelineError):
    """Claude API call failed or returned an unusable response."""

    code = "claude_failed"
    http_status = 502
    retryable = True


class UpstreamError(PipelineError):
    """An upstream API (Apollo or Exa) returned a non-2xx response."""

    code = "upstream_error"
    http_status = 502
    retryable = True
