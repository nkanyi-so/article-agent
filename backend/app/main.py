from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.schemas import HealthResponse, RunsResponse

app = FastAPI(title="article-agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="article-agent", version="0.1.0")


@app.get("/api/runs", response_model=RunsResponse)
async def list_runs() -> RunsResponse:
    # Phase 0 stub — no runs yet.
    return RunsResponse(runs=[])
