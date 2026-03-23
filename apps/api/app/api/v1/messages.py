from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.message import MessageCreate, MessageOut
from app.services.assistant_service import generate_message_id
from app.services.chat_service import build_llm_messages, resolve_conversation_context, serialize_sources, summarize_details
from app.services.knowledge_service import RetrievedKnowledge, retrieve_relevant_chunks
from app.services.llm_provider import OpenAICompatibleProviderAdapter, ProviderConfigurationError
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded
from app.utils.sse import sse_event

router = APIRouter()


async def get_conversation_or_404(session: AsyncSession, conversation_id: str, user_id: str) -> Conversation:
    conversation = await session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.provider_connection))
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Conversation.id == conversation_id, Workspace.owner_id == user_id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("")
async def list_messages(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    conversation_id: str = Query(...),
):
    await get_conversation_or_404(session, conversation_id, user.id)
    result = await session.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()))
    items = [MessageOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)


@router.post("")
async def create_message(
    payload: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    conversation = await get_conversation_or_404(session, payload.conversation_id, user.id)
    resolved = await resolve_conversation_context(session, conversation, user_id=user.id)
    retrieved_knowledge = await maybe_retrieve_knowledge(session, conversation, payload, user.id)
    llm_messages = await build_llm_messages(session, conversation, payload.content, retrieved_knowledge)

    user_message = Message(id=generate_message_id("user"), conversation_id=payload.conversation_id, role="user", content=payload.content)
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    execution = await create_runtime_execution(
        session,
        workspace_id=resolved.workspace.id,
        user_id=user.id,
        source="chat",
        provider_id=resolved.provider.id if resolved.provider else None,
        model_id=resolved.model.id if resolved.model else None,
        provider_connection_id=resolved.provider_connection.provider_connection_id,
        resolved_model_name=resolved.model_name,
        resolved_base_url=resolved.provider_connection.base_url,
        conversation_id=conversation.id,
        prompt_preview=payload.content[:400],
        details_json=summarize_details(retrieved_knowledge),
    )

    try:
        await mark_runtime_running(session, execution)
        adapter = OpenAICompatibleProviderAdapter(
            api_key=resolved.provider_connection.api_key,
            base_url=resolved.provider_connection.base_url,
        )
        completion = await adapter.complete_chat(resolved.model_name, llm_messages)
        assistant_message = Message(
            id=generate_message_id("assistant"),
            conversation_id=payload.conversation_id,
            runtime_execution_id=execution.id,
            role="assistant",
            content=completion.content,
            sources_json=serialize_sources(retrieved_knowledge),
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=completion.content[:400],
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
            details_json=summarize_details(retrieved_knowledge),
        )
    except Exception as exc:
        await mark_runtime_failed(session, execution, error_message=str(exc), details_json=summarize_details(retrieved_knowledge))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return success_response(
        {
            "user_message": MessageOut.model_validate(user_message).model_dump(),
            "assistant_message": MessageOut.model_validate(assistant_message).model_dump(),
            "runtime_execution_id": execution.id,
        }
    )


@router.post("/stream")
async def stream_message(
    payload: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    conversation = await get_conversation_or_404(session, payload.conversation_id, user.id)
    resolved = await resolve_conversation_context(session, conversation, user_id=user.id)

    async def event_generator():
        user_message = Message(id=generate_message_id("user"), conversation_id=payload.conversation_id, role="user", content=payload.content)
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        retrieved_knowledge = await maybe_retrieve_knowledge(session, conversation, payload, user.id)
        llm_messages = await build_llm_messages(session, conversation, payload.content, retrieved_knowledge)
        execution = await create_runtime_execution(
            session,
            workspace_id=resolved.workspace.id,
            user_id=user.id,
            source="chat",
            provider_id=resolved.provider.id if resolved.provider else None,
            model_id=resolved.model.id if resolved.model else None,
            provider_connection_id=resolved.provider_connection.provider_connection_id,
            resolved_model_name=resolved.model_name,
            resolved_base_url=resolved.provider_connection.base_url,
            conversation_id=conversation.id,
            prompt_preview=payload.content[:400],
            details_json=summarize_details(retrieved_knowledge),
        )

        yield sse_event(
            "message_start",
            {
                "conversation_id": payload.conversation_id,
                "message_id": user_message.id,
                "runtime_execution_id": execution.id,
                "sources": serialize_sources(retrieved_knowledge),
                "provider_connection_name": resolved.provider_connection.provider_connection_name,
                "model_name": resolved.model_name,
            },
        )

        assistant_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            await mark_runtime_running(session, execution)
            adapter = OpenAICompatibleProviderAdapter(
                api_key=resolved.provider_connection.api_key,
                base_url=resolved.provider_connection.base_url,
            )
            async for chunk in adapter.stream_chat(resolved.model_name, llm_messages):
                if chunk.delta:
                    assistant_content += chunk.delta
                    yield sse_event("delta", {"delta": chunk.delta})
                if chunk.usage is not None:
                    usage = chunk.usage.model_dump()

            assistant_message = Message(
                id=generate_message_id("assistant"),
                conversation_id=payload.conversation_id,
                runtime_execution_id=execution.id,
                role="assistant",
                content=assistant_content,
                sources_json=serialize_sources(retrieved_knowledge),
            )
            session.add(assistant_message)
            await session.commit()
            await session.refresh(assistant_message)
            await mark_runtime_succeeded(
                session,
                execution,
                response_preview=assistant_content[:400],
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                details_json=summarize_details(retrieved_knowledge),
            )
            yield sse_event(
                "finish",
                {
                    "message_id": assistant_message.id,
                    "content": assistant_content,
                    "sources": serialize_sources(retrieved_knowledge),
                    "runtime_execution_id": execution.id,
                    "usage": usage,
                    "provider_connection_name": resolved.provider_connection.provider_connection_name,
                    "model_name": resolved.model_name,
                },
            )
        except ProviderConfigurationError as exc:
            await mark_runtime_failed(session, execution, error_message=str(exc), details_json=summarize_details(retrieved_knowledge))
            yield sse_event("error", {"message": str(exc), "runtime_execution_id": execution.id})
        except Exception as exc:
            await mark_runtime_failed(session, execution, error_message=str(exc), details_json=summarize_details(retrieved_knowledge))
            yield sse_event("error", {"message": str(exc), "runtime_execution_id": execution.id})
        finally:
            yield sse_event("done", {"ok": True})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def maybe_retrieve_knowledge(
    session: AsyncSession, conversation: Conversation, payload: MessageCreate, user_id: str
) -> RetrievedKnowledge | None:
    use_knowledge = payload.use_knowledge if payload.use_knowledge is not None else conversation.use_knowledge
    if not use_knowledge:
        return None
    return await retrieve_relevant_chunks(session, workspace_id=conversation.workspace_id, query=payload.content, user_id=user_id)
