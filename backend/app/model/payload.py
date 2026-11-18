"""What is actually sent to the model for a request, and the key that names it.

The key is taken over the API arguments, not over the request object, so a change in how
a request is sent (a thinking setting, the citations flag) makes old recordings miss just
as a prompt edit does.
"""

import hashlib
import json
from typing import Any

from app.model.types import DocumentPart, ModelRequest


def api_request(request: ModelRequest) -> dict[str, Any]:
    """The Messages API arguments for a request. Transcript text travels only inside a
    document block (cited by block index) or inside whatever delimited text the stage built."""
    content: list[dict[str, Any]] = []
    for part in request.content:
        if isinstance(part, DocumentPart):
            content.append(
                {
                    "type": "document",
                    "source": {
                        "type": "content",
                        "content": [{"type": "text", "text": block} for block in part.blocks],
                    },
                    "title": part.title,
                    "citations": {"enabled": True},
                }
            )
        else:
            content.append({"type": "text", "text": part.text})
    output_config: dict[str, Any] = {"effort": request.effort}
    if request.output_schema is not None:
        # Citations and an output schema cannot be combined; the stages never ask for both.
        output_config["format"] = {"type": "json_schema", "schema": request.output_schema}
    return {
        "model": request.model,
        "max_tokens": request.max_tokens,
        "system": request.system,
        "thinking": {"type": "adaptive"},
        "output_config": output_config,
        "messages": [{"role": "user", "content": content}],
    }


def request_key(request: ModelRequest) -> str:
    """SHA-256 of the canonical API arguments. Any change to a prompt, a block, a setting or
    the way they are sent changes it, so a recording can never answer a question that is
    no longer the one being asked."""
    canonical = json.dumps(
        api_request(request), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
