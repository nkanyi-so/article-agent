"""Which model does what, and at what effort. One place, set explicitly (decisions/0005)."""

from app.model.types import Effort

WRITER_MODEL = "claude-sonnet-5-5"
EXTRACT_EFFORT: Effort = "low"
DRAFT_EFFORT: Effort = "medium"
# Thinking tokens count toward this, so it is well above what an article needs.
MAX_TOKENS = 16_000
