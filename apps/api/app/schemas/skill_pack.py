from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class SkillPackOut(TimestampedModel):
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
    tool_capabilities_json: list[str] | dict[str, Any] | None = None
    last_synced_at: datetime | None = None


class SkillPackImportPayload(BaseModel):
    workspace_id: str
    source_path: str


class SkillPackImportResult(BaseModel):
    pack: SkillPackOut
    imported_skill_count: int


class SkillPackSyncResult(BaseModel):
    synced_pack_count: int
    synced_skill_count: int
