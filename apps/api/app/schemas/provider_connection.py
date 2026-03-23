from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel


class ProviderConnectionModelWrite(BaseModel):
    name: str = Field(min_length=1)
    kind: str = "chat"
    source: str = "manual"


class ProviderConnectionCreate(BaseModel):
    provider_type: str = "openai_compatible"
    name: str
    base_url: str
    api_key: str | None = None
    model_discovery_mode: str = "auto"
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None
    manual_models: list[ProviderConnectionModelWrite] | None = None


class ProviderConnectionUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_discovery_mode: str | None = None
    status: str | None = None
    is_enabled: bool | None = None
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None
    manual_models: list[ProviderConnectionModelWrite] | None = None


class MaskedSecretMeta(BaseModel):
    masked_value: str | None = None
    configured: bool


class ProviderConnectionModelOut(BaseModel):
    name: str
    kind: str = "chat"
    source: str = "discovered"
    metadata: dict[str, Any] | None = None


class ProviderConnectionTestResult(BaseModel):
    ok: bool
    status: str
    message: str
    last_checked_at: datetime | None = None
    discovered_model_count: int = 0


class ProviderConnectionOut(TimestampedModel):
    id: str
    user_id: str
    provider_id: str | None = None
    provider_type: str
    name: str
    base_url: str
    model_discovery_mode: str
    status: str
    is_enabled: bool
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None
    secret: MaskedSecretMeta
    models: list[ProviderConnectionModelOut] = []
    last_checked_at: datetime | None = None
    last_error: str | None = None
