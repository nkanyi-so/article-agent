"""The app factory. Importing this module needs no key and reads no file."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app import __version__
from app.settings import Mode, Settings, load_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
    mode: Mode
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="article-agent", version=__version__)

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", mode=settings.mode, version=__version__)

    return app
