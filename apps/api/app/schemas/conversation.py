from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class ConversationCreate(BaseModel):
    workspace_id: str
    title: str
    id: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    provider_connection_id: str | None = None
    model_name: str | None = None
    use_knowledge: bool = False


class ConversationUpdate(BaseModel):
    title: str | None = None
    provider_connection_id: str | None = None
    model_name: str | None = None
    use_knowledge: bool | None = None


class ConversationOut(TimestampedModel):
    id: str
    workspace_id: str
    title: str
    created_by_id: str
    provider_id: str | None = None
    model_id: str | None = None
    provider_connection_id: str | None = None
    provider_connection_name: str | None = None
    model_name: str | None = None
    use_knowledge: bool = False
