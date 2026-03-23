from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class KnowledgeDocumentOut(TimestampedModel):
    id: str
    workspace_id: str
    file_name: str
    title: str | None = None
    file_type: str
    status: str
    source_type: str
    source_ref: str | None = None
    knowledge_pack_slug: str | None = None
    storage_path: str
    content_length: int
    chunk_count: int
    error_message: str | None = None


class KnowledgePackOut(TimestampedModel):
    id: str
    workspace_id: str
    slug: str
    name: str
    version: str
    description: str
    source_type: str
    source_ref: str | None = None
    manifest_path: str | None = None
    is_builtin: bool
    status: str
    last_synced_at: datetime | None = None


class KnowledgePackSyncResult(BaseModel):
    synced_pack_count: int
    synced_document_count: int
