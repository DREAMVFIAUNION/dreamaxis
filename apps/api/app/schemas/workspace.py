from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class WorkspaceCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    workspace_root_path: str | None = None
    default_provider_id: str | None = None
    default_model_id: str | None = None
    default_provider_connection_id: str | None = None
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None


class WorkspaceOut(TimestampedModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    owner_id: str
    workspace_root_path: str | None = None
    default_provider_id: str | None = None
    default_model_id: str | None = None
    default_provider_connection_id: str | None = None
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None
