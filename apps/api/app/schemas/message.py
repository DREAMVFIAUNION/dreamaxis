from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


ChatMode = Literal[
    "understand_repo",
    "inspect_repo",
    "verify_repo",
    "propose_fix",
    "inspect_desktop",
    "verify_desktop",
    "operate_desktop",
]


class MessageCreate(BaseModel):
    conversation_id: str
    content: str
    use_knowledge: bool | None = None
    mode: ChatMode | None = None


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
