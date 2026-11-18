"""The live client. The only module in the application that imports the Anthropic SDK.

It is loaded only when the app is started in live mode, and the SDK is installed only
by the `live` dependency group, so the hosted demo can neither import nor reach it.
"""

import time
from collections.abc import Callable
from typing import Any, Literal

import anthropic

from app.errors import MissingKey, ModelCallFailed
from app.model.convert import billed_usd, response_from_api
from app.model.payload import api_request
from app.model.types import ModelRequest, ModelResponse

# Set explicitly: the SDK's defaults are ten minutes and two retries.
TIMEOUT_S = 60.0
MAX_RETRIES = 1

OnBilled = Callable[[ModelRequest, float | None], None]
OnRaw = Callable[[ModelRequest, ModelResponse, dict[str, Any]], None]


class LiveModelClient:
    source: Literal["live"] = "live"

    def __init__(
        self, api_key: str | None, on_raw: OnRaw | None = None, on_billed: OnBilled | None = None
    ) -> None:
        if not api_key:
            raise MissingKey
        # No fallback model is configured: a run whose writer silently changed would make
        # the eval table untrue (decisions/0005).
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, timeout=TIMEOUT_S, max_retries=MAX_RETRIES
        )
        self._on_raw = on_raw
        self._on_billed = on_billed
        self.last_raw: dict[str, Any] | None = None

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.last_raw = None
        started = time.monotonic()
        try:
            raw = await self._client.messages.with_raw_response.create(**api_request(request))
            message = await raw.parse()
        except anthropic.APIStatusError as error:
            # The status only. The body is upstream text and stays out of our errors.
            raise ModelCallFailed(f"status {error.status_code}") from error
        except anthropic.APIConnectionError as error:  # includes timeouts
            raise ModelCallFailed(type(error).__name__) from error
        latency_ms = round((time.monotonic() - started) * 1000)
        self.last_raw = message.to_dict()
        # A response arrived, so the call was billed, whether or not it turns out usable.
        # Tell whoever is counting before anything can raise.
        if self._on_billed:
            self._on_billed(request, billed_usd(self.last_raw, request))
        response = response_from_api(
            self.last_raw,
            request,
            latency_ms=latency_ms,
            attempts=raw.retries_taken + 1,
            request_id=raw.headers.get("request-id"),
        )
        if self._on_raw:
            self._on_raw(request, response, self.last_raw)
        return response
