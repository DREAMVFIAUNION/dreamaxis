from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class MessageCreate(BaseModel):
    conversation_id: str
    content: str
    use_knowledge: bool | None = None


class KnowledgeChunkReference(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    excerpt: str
    score: float


class ModelUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class MessageOut(TimestampedModel):
    id: str
    conversation_id: str
    runtime_execution_id: str | None = None
    role: str
    content: str
    sources_json: list[dict] | None = None
