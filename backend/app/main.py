"""The app factory. Importing this module needs no key."""

from collections.abc import AsyncIterable
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

from app import __version__
from app.model.fixture import FixtureModelClient
from app.model.types import ModelClient
from app.settings import Mode, Settings, load_settings
from app.skeleton import RuntimeReport, SkeletonEvent, runtime_report, skeleton_events


class HealthResponse(BaseModel):
    status: Literal["ok"]
    mode: Mode
    version: str


def build_model_client(settings: Settings) -> ModelClient:
    """The mode is chosen once, here. Demo mode never loads the live client's module."""
    if settings.mode == "live":
        from app.model.live import LiveModelClient

        key = settings.anthropic_api_key
        return LiveModelClient(key.get_secret_value() if key else None)
    return FixtureModelClient()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="article-agent", version=__version__)
    app.state.model_client = build_model_client(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", mode=settings.mode, version=__version__)

    if settings.skeleton_routes:
        add_skeleton_routes(app, settings)
    return app


def add_skeleton_routes(app: FastAPI, settings: Settings) -> None:
    """The Phase 2 routes that prove the host. Off by default; Phase 5 deletes them.

    They are public and unmetered, and one of them lists what is installed, so they
    are registered only where `APP_SKELETON_ROUTES` is switched on.
    """

    @app.get("/skeleton/stream", response_class=EventSourceResponse)
    async def skeleton_stream() -> AsyncIterable[SkeletonEvent]:
        async for event in skeleton_events(settings.skeleton_delay_s):
            yield SkeletonEvent(event)

    @app.get("/skeleton/runtime")
    async def skeleton_runtime() -> RuntimeReport:
        return runtime_report()


# The host's Python runtime looks for a module-level ASGI application.
app = create_app()
