from __future__ import annotations

from app.schemas.common import TimestampedModel


class AIModelOut(TimestampedModel):
    id: str
    provider_id: str
    slug: str
    name: str
    kind: str
    context_window: int
    is_default: bool
