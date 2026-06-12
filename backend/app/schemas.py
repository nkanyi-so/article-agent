from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class RunsResponse(BaseModel):
    runs: list[dict]
