from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai_model import AIModel
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.provider import Provider
from app.models.workspace import Workspace
from app.services.llm_provider import ProviderConfigurationError
from app.services.provider_connections import ResolvedProviderConnection, resolve_provider_connection_or_fallback

settings = get_settings()

if TYPE_CHECKING:
    from app.services.knowledge_service import RetrievedKnowledge


@dataclass
class ResolvedConversationContext:
    workspace: Workspace
    provider: Provider | None
    model: AIModel | None
    provider_connection: ResolvedProviderConnection
    model_name: str


@dataclass
class ResolvedEmbeddingContext:
    workspace: Workspace
    provider_connection: ResolvedProviderConnection
    model_name: str


async def resolve_conversation_context(
    session: AsyncSession,
    conversation: Conversation,
    *,
    user_id: str,
) -> ResolvedConversationContext:
    workspace = await session.scalar(select(Workspace).where(Workspace.id == conversation.workspace_id))
    if not workspace:
        raise RuntimeError("Workspace not found for conversation")

    provider_id = conversation.provider_id or workspace.default_provider_id
    model_id = conversation.model_id or workspace.default_model_id
    provider = await session.scalar(select(Provider).where(Provider.id == provider_id)) if provider_id else None
    model = await session.scalar(select(AIModel).where(AIModel.id == model_id)) if model_id else None
    if provider is None and model is not None:
        provider = await session.scalar(select(Provider).where(Provider.id == model.provider_id))

    provider_connection = await resolve_provider_connection_or_fallback(
        session,
        user_id=user_id,
        connection_id=conversation.provider_connection_id or workspace.default_provider_connection_id,
    )
    if provider_connection is None:
        raise ProviderConfigurationError("No provider connection is configured. Add an API key from Provider Settings.")

    resolved_model_name = (
        conversation.model_name
        or provider_connection.default_model_name
        or workspace.default_model_name
        or (model.slug if model else None)
        or settings.OPENAI_CHAT_MODEL
    )

    return ResolvedConversationContext(
        workspace=workspace,
        provider=provider,
        model=model,
        provider_connection=provider_connection,
        model_name=resolved_model_name,
    )


async def resolve_workspace_embedding_context(
    session: AsyncSession,
    workspace: Workspace,
    *,
    user_id: str,
) -> ResolvedEmbeddingContext:
    provider_connection = await resolve_provider_connection_or_fallback(
        session,
        user_id=user_id,
        connection_id=workspace.default_provider_connection_id,
    )
    if provider_connection is None:
        raise ProviderConfigurationError("No provider connection is configured for embeddings. Add an API key from Provider Settings.")

    embedding_model = await session.scalar(
        select(AIModel).where(AIModel.kind == "embedding").order_by(AIModel.is_default.desc(), AIModel.created_at.asc())
    )
    resolved_model_name = (
        workspace.default_embedding_model_name
        or provider_connection.default_embedding_model_name
        or (embedding_model.slug if embedding_model else None)
        or settings.OPENAI_EMBEDDING_MODEL
    )
    return ResolvedEmbeddingContext(workspace=workspace, provider_connection=provider_connection, model_name=resolved_model_name)


async def build_llm_messages(
    session: AsyncSession,
    conversation: Conversation,
    user_prompt: str,
    retrieved_knowledge: RetrievedKnowledge | None = None,
    additional_system_prompt: str | None = None,
    history_limit: int = 12,
) -> list[dict[str, str]]:
    recent_messages = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(history_limit)
    )
    history = list(reversed(recent_messages.scalars().all()))

    system_parts = [
        "You are DreamAxis, an operator-facing AI execution console.",
        "Respond in clear operational language with concise steps, concrete outcomes, and explicit risks when relevant.",
    ]
    if additional_system_prompt:
        system_parts.append(additional_system_prompt)
    if retrieved_knowledge and retrieved_knowledge.context:
        system_parts.append(
            "Use the following knowledge context when it is relevant. If it is not relevant, do not force it into the answer.\n\n"
            + retrieved_knowledge.context
        )

    payload: list[dict[str, str]] = [{"role": "system", "content": "\n\n".join(system_parts)}]
    for message in history:
        payload.append({"role": message.role, "content": message.content})
    if not history or history[-1].role != "user" or history[-1].content != user_prompt:
        payload.append({"role": "user", "content": user_prompt})
    return payload


def serialize_sources(retrieved_knowledge: RetrievedKnowledge | None) -> list[dict] | None:
    if not retrieved_knowledge or not retrieved_knowledge.sources:
        return None
    return [source.model_dump() for source in retrieved_knowledge.sources]


def summarize_details(retrieved_knowledge: RetrievedKnowledge | None) -> dict | None:
    if not retrieved_knowledge or not retrieved_knowledge.sources:
        return None
    return {"knowledge_sources": [source.model_dump() for source in retrieved_knowledge.sources]}
