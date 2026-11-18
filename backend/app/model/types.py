"""What a stage asks of a model, and what comes back. A recording is these two, serialised."""

from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.schemas import DraftBlock

Effort = Literal["low", "medium", "high"]


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class DocumentPart(BaseModel):
    """A citable document: one block per transcript sentence, cited by block index."""

    type: Literal["document"] = "document"
    title: str
    blocks: list[str]


ContentPart = Annotated[TextPart | DocumentPart, Field(discriminator="type")]


class ModelRequest(BaseModel):
    model: str
    system: str
    content: list[ContentPart]
    output_schema: dict[str, Any] | None = None
    max_tokens: int = Field(gt=0)
    effort: Effort


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    thinking_tokens: int = 0


class ModelResponse(BaseModel):
    blocks: list[DraftBlock] = Field(description="The text blocks, with any citations.")
    parsed: dict[str, Any] | None = Field(description="The object, when a schema was given.")
    stop_reason: str
    model: str = Field(description="The model that served the request.")
    usage: Usage
    cost_usd: float
    latency_ms: int
    attempts: int = 1
    request_id: str | None = None


class ModelClient(Protocol):
    """The one way any stage reaches a model."""

    @property
    def source(self) -> Literal["live", "fixture"]: ...

    async def complete(self, request: ModelRequest) -> ModelResponse: ...
