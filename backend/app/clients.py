from __future__ import annotations

from datetime import datetime, timezone

import anthropic
import anyio
import httpx
from exa_py import Exa

from app import settings
from app.errors import ClaudeError, UpstreamError


# ---------------------------------------------------------------------------
# Exa result wrapper
# ---------------------------------------------------------------------------


class ExaHit:
    """Lightweight wrapper around a single Exa search result."""

    def __init__(self, raw: object, idx: int) -> None:
        self.id: str = f"exa:{idx}"
        self.url: str | None = getattr(raw, "url", None)
        self.title: str | None = getattr(raw, "title", None)
        self.published_date: str | None = getattr(raw, "published_date", None)
        self.text: str | None = getattr(raw, "text", None)
        self.highlights: list[str] = list(getattr(raw, "highlights", None) or [])


# ---------------------------------------------------------------------------
# Apollo client  (async-native via httpx)
# ---------------------------------------------------------------------------


class ApolloClient:
    _MATCH_URL = "https://api.apollo.io/api/v1/people/match"
    _SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"

    def __init__(
        self,
        api_key: str | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        # Raises MissingKeyError immediately if key absent.
        self._key = api_key or settings.apollo_key()
        self._owns_http = http is None
        self._http = http or httpx.AsyncClient(timeout=20.0)

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._key, "Content-Type": "application/json"}

    async def match(
        self,
        *,
        name: str | None = None,
        organization_name: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict:
        """POST /api/v1/people/match — returns the full JSON response."""
        body: dict = {}
        if name:
            body["name"] = name
        if organization_name:
            body["organization_name"] = organization_name
        if domain:
            body["domain"] = domain
        if linkedin_url:
            body["linkedin_url"] = linkedin_url

        resp = await self._http.post(self._MATCH_URL, json=body, headers=self._headers())
        if resp.status_code != 200:
            raise UpstreamError(
                f"Apollo people/match returned HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    async def search(
        self,
        *,
        q_keywords: str,
        page: int = 1,
        per_page: int = 10,
    ) -> dict:
        """POST /api/v1/mixed_people/api_search — returns the full JSON response."""
        body: dict = {"q_keywords": q_keywords, "page": page, "per_page": per_page}
        resp = await self._http.post(self._SEARCH_URL, json=body, headers=self._headers())
        if resp.status_code != 200:
            raise UpstreamError(
                f"Apollo api_search returned HTTP {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()


# ---------------------------------------------------------------------------
# Exa client  (sync SDK offloaded to a thread)
# ---------------------------------------------------------------------------


class ExaClient:
    def __init__(
        self,
        api_key: str | None = None,
        exa: Exa | None = None,
    ) -> None:
        # Raises MissingKeyError immediately if key absent.
        self._exa = exa or Exa(api_key=api_key or settings.exa_key())

    async def search_news(
        self,
        query: str,
        *,
        start_published_date: str,
        num_results: int = 8,
    ) -> list[ExaHit]:
        """Search Exa for recent news and return ExaHit wrappers."""

        def _call() -> object:
            return self._exa.search_and_contents(
                query,
                category="news",
                start_published_date=start_published_date,
                num_results=num_results,
                text=True,
                highlights=True,
            )

        result = await anyio.to_thread.run_sync(_call)
        return [ExaHit(r, i) for i, r in enumerate(result.results)]


# ---------------------------------------------------------------------------
# Claude client  (sync SDK offloaded to a thread)
# ---------------------------------------------------------------------------


class ClaudeClient:
    MODEL = "claude-opus-4-8"

    def __init__(
        self,
        api_key: str | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        # Raises MissingKeyError immediately if key absent.
        key = api_key or settings.anthropic_key()
        self._c = client or anthropic.Anthropic(api_key=key)

    async def parse(
        self,
        *,
        messages: list[dict],
        output_format: type,
        max_tokens: int = 4096,
    ) -> object:
        """Call Claude with structured output, returning the parsed Pydantic instance."""

        def _call() -> object:
            return self._c.messages.parse(
                model=self.MODEL,
                messages=messages,
                output_format=output_format,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
            )

        try:
            resp = await anyio.to_thread.run_sync(_call)
        except anthropic.APIError as exc:
            raise ClaudeError(f"Claude API error: {exc}") from exc

        if resp is None or not hasattr(resp, "parsed_output"):
            raise ClaudeError("Claude returned no parsed output")
        if resp.parsed_output is None:
            raise ClaudeError("Claude structured-output parsing failed")
        return resp.parsed_output


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------


class Clients:
    """All three API clients built once per pipeline run.

    Building this object validates that all three keys are present —
    raises MissingKeyError before any network call is made.
    """

    def __init__(self) -> None:
        self.apollo = ApolloClient()
        self.exa = ExaClient()
        self.claude = ClaudeClient()

    async def aclose(self) -> None:
        await self.apollo.aclose()
