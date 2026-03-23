from __future__ import annotations

from app.schemas.common import TimestampedModel


class ProviderOut(TimestampedModel):
    id: str
    slug: str
    name: str
    type: str
    status: str
