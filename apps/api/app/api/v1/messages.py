from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAIError
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
from app.services.desktop_operator import (
    build_desktop_operator_fallback_response,
    build_desktop_operator_response_prompt,
    collect_desktop_operator_trace,
)
from app.services.knowledge_service import RetrievedKnowledge, retrieve_relevant_chunks
from app.services.llm_provider import OpenAICompatibleProviderAdapter, ProviderConfigurationError
from app.services.operator_plans import sync_operator_plan_from_trace
from app.services.repo_copilot import (
    build_repo_copilot_fallback_response,
    build_repo_copilot_response_prompt,
    collect_repo_copilot_trace,
    normalize_repo_copilot_response,
)
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded
from app.utils.sse import sse_event

router = APIRouter()
DESKTOP_CHAT_MODES = {"inspect_desktop", "verify_desktop", "operate_desktop"}


def should_route_desktop_turn(payload: MessageCreate) -> bool:
    if payload.mode in DESKTOP_CHAT_MODES:
        return True
    lowered = payload.content.lower()
    desktop_tokens = [
        "desktop",
        "window",
        "windows app",
        "focus window",
        "active window",
        "screenshot",
        "ocr",
        "screen",
        "vs code",
        "vscode",
        "terminal",
        "browser tab",
        "click",
        "type into",
        "open app",
        "launch app",
    ]
    return any(token in lowered for token in desktop_tokens)


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


def merge_runtime_details(base_details: dict | None, trace: dict | None = None) -> dict | None:
    payload = dict(base_details or {})
    if trace is not None:
        payload["mode"] = trace.get("mode")
        payload["execution_bundle_id"] = trace.get("execution_bundle_id")
        payload["child_execution_ids"] = trace.get("child_execution_ids") or []
        payload["proposal"] = trace.get("proposal")
        payload["workspace_readiness"] = trace.get("workspace_readiness")
        payload["execution_trace"] = trace
        payload["evidence_items"] = trace.get("evidence_items") or trace.get("evidence") or []
        payload["recommended_next_actions"] = trace.get("recommended_next_actions") or []
        payload["trace_summary"] = trace.get("trace_summary")
    return payload or None


def build_trace_response_metadata(trace: dict | None) -> dict:
    trace = trace or {}
    return {
        "mode": trace.get("mode"),
        "execution_bundle_id": trace.get("execution_bundle_id"),
        "grounding_summary": trace.get("grounding_summary"),
        "desktop_grounding_summary": trace.get("desktop_grounding_summary"),
        "primary_grounded_target": trace.get("primary_grounded_target"),
        "reflection_summary": trace.get("reflection_summary"),
        "evidence_items": trace.get("evidence_items") or trace.get("evidence") or [],
        "proposal": trace.get("proposal"),
        "desktop_action_approval": trace.get("desktop_action_approval"),
        "requested_desktop_actions": trace.get("requested_desktop_actions") or [],
        "workflow_stage": trace.get("workflow_stage"),
        "operator_plan_id": trace.get("operator_plan_id"),
        "operator_plan_status": trace.get("operator_plan_status"),
        "operator_stage": trace.get("operator_stage"),
        "active_step_id": trace.get("active_step_id"),
        "pending_approval_count": trace.get("pending_approval_count"),
        "latest_artifact_summaries": trace.get("latest_artifact_summaries") or trace.get("artifact_summaries") or [],
        "step_verification_summary": trace.get("step_verification_summary"),
        "workspace_readiness": trace.get("workspace_readiness"),
        "recommended_next_actions": trace.get("recommended_next_actions") or [],
    }


def build_trace_fallback_content(trace: dict | None, exc: Exception | None = None) -> str:
    content = build_repo_copilot_fallback_response(trace or {})
    if isinstance(exc, OpenAIError):
        content += (
            "\n\n> DreamAxis could not reach the configured model, so this answer was assembled directly from local "
            "execution evidence."
        )
    return content


def build_desktop_trace_fallback_content(trace: dict | None, exc: Exception | None = None) -> str:
    content = build_desktop_operator_fallback_response(trace or {})
    if isinstance(exc, OpenAIError):
        content += (
            "\n\n> DreamAxis could not reach the configured model, so this desktop operator response was assembled "
            "directly from local runtime evidence and approval state."
        )
    return content


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
    workspace = await session.scalar(select(Workspace).where(Workspace.id == conversation.workspace_id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    user_message = Message(id=generate_message_id("user"), conversation_id=payload.conversation_id, role="user", content=payload.content)
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    retrieved_knowledge = await maybe_retrieve_knowledge(session, conversation, payload, user.id)
    trace_sources = serialize_sources(retrieved_knowledge)
    trace = None
    route_desktop = should_route_desktop_turn(payload)

    execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="chat",
        provider_id=conversation.provider_id,
        model_id=conversation.model_id,
        provider_connection_id=conversation.provider_connection_id,
        resolved_model_name=conversation.model_name,
        resolved_base_url=conversation.provider_connection.base_url if conversation.provider_connection else None,
        conversation_id=conversation.id,
        prompt_preview=payload.content[:400],
        details_json={**(summarize_details(retrieved_knowledge) or {}), "requested_mode": payload.mode},
    )

    try:
        await mark_runtime_running(session, execution)
        if route_desktop:
            trace = await collect_desktop_operator_trace(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=execution,
                prompt=payload.content,
                mode=payload.mode,
                knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
            )
            _, trace = await sync_operator_plan_from_trace(
                session,
                workspace_id=workspace.id,
                created_by_id=user.id,
                requested_prompt=payload.content,
                trace=trace,
                parent_execution_id=execution.id,
                conversation_id=conversation.id,
            )
            additional_system_prompt = build_desktop_operator_response_prompt(trace)
        else:
            trace = await collect_repo_copilot_trace(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=execution,
                prompt=payload.content,
                mode=payload.mode,
                knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
            )
            additional_system_prompt = build_repo_copilot_response_prompt(trace)
        resolved = await resolve_conversation_context(session, conversation, user_id=user.id)
        llm_messages = await build_llm_messages(
            session,
            conversation,
            payload.content,
            retrieved_knowledge,
            additional_system_prompt=additional_system_prompt,
        )
        adapter = OpenAICompatibleProviderAdapter(
            api_key=resolved.provider_connection.api_key,
            base_url=resolved.provider_connection.base_url,
        )
        completion = await adapter.complete_chat(resolved.model_name, llm_messages)
        normalized_content = (
            completion.content
            if route_desktop
            else normalize_repo_copilot_response(completion.content, trace)
        )
        assistant_message = Message(
            id=generate_message_id("assistant"),
            conversation_id=payload.conversation_id,
            runtime_execution_id=execution.id,
            role="assistant",
            content=normalized_content,
            sources_json=trace_sources,
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=normalized_content[:400],
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
            details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
        )
    except (ProviderConfigurationError, OpenAIError) as exc:
        trace = trace or (
            await collect_desktop_operator_trace(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=execution,
                prompt=payload.content,
                mode=payload.mode,
                knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
            )
            if route_desktop
            else await collect_repo_copilot_trace(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=execution,
                prompt=payload.content,
                mode=payload.mode,
                knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
            )
        )
        if route_desktop and isinstance(trace, dict):
            _, trace = await sync_operator_plan_from_trace(
                session,
                workspace_id=workspace.id,
                created_by_id=user.id,
                requested_prompt=payload.content,
                trace=trace,
                parent_execution_id=execution.id,
                conversation_id=conversation.id,
            )
        fallback_content = (
            build_desktop_trace_fallback_content(trace, exc)
            if route_desktop
            else build_trace_fallback_content(trace, exc)
        )
        assistant_message = Message(
            id=generate_message_id("assistant"),
            conversation_id=payload.conversation_id,
            runtime_execution_id=execution.id,
            role="assistant",
            content=fallback_content,
            sources_json=trace_sources,
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=fallback_content[:400],
            details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
        )
    except Exception as exc:
        await mark_runtime_failed(
            session,
            execution,
            error_message=str(exc),
            details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return success_response(
        {
            "user_message": MessageOut.model_validate(user_message).model_dump(),
            "assistant_message": MessageOut.model_validate(assistant_message).model_dump(),
            "runtime_execution_id": execution.id,
            "runtime_execution_ids": (trace or {}).get("runtime_execution_ids", []),
            "execution_trace": trace,
            **build_trace_response_metadata(trace),
        }
    )


@router.post("/stream")
async def stream_message(
    payload: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    conversation = await get_conversation_or_404(session, payload.conversation_id, user.id)
    workspace = await session.scalar(select(Workspace).where(Workspace.id == conversation.workspace_id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    async def event_generator():
        user_message = Message(id=generate_message_id("user"), conversation_id=payload.conversation_id, role="user", content=payload.content)
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        retrieved_knowledge = await maybe_retrieve_knowledge(session, conversation, payload, user.id)
        trace_sources = serialize_sources(retrieved_knowledge)
        route_desktop = should_route_desktop_turn(payload)
        execution = await create_runtime_execution(
            session,
            workspace_id=workspace.id,
            user_id=user.id,
            source="chat",
            execution_kind="chat",
            provider_id=conversation.provider_id,
            model_id=conversation.model_id,
            provider_connection_id=conversation.provider_connection_id,
            resolved_model_name=conversation.model_name,
            resolved_base_url=conversation.provider_connection.base_url if conversation.provider_connection else None,
            conversation_id=conversation.id,
            prompt_preview=payload.content[:400],
            details_json={**(summarize_details(retrieved_knowledge) or {}), "requested_mode": payload.mode},
        )

        assistant_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        trace = None
        message_started = False

        try:
            await mark_runtime_running(session, execution)
            if route_desktop:
                trace = await collect_desktop_operator_trace(
                    session,
                    workspace=workspace,
                    user=user,
                    conversation=conversation,
                    parent_execution=execution,
                    prompt=payload.content,
                    mode=payload.mode,
                    knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
                )
                _, trace = await sync_operator_plan_from_trace(
                    session,
                    workspace_id=workspace.id,
                    created_by_id=user.id,
                    requested_prompt=payload.content,
                    trace=trace,
                    parent_execution_id=execution.id,
                    conversation_id=conversation.id,
                )
                additional_system_prompt = build_desktop_operator_response_prompt(trace)
            else:
                trace = await collect_repo_copilot_trace(
                    session,
                    workspace=workspace,
                    user=user,
                    conversation=conversation,
                    parent_execution=execution,
                    prompt=payload.content,
                    mode=payload.mode,
                    knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
                )
                additional_system_prompt = build_repo_copilot_response_prompt(trace)
            resolved = await resolve_conversation_context(session, conversation, user_id=user.id)
            llm_messages = await build_llm_messages(
                session,
                conversation,
                payload.content,
                retrieved_knowledge,
                additional_system_prompt=additional_system_prompt,
            )
            yield sse_event(
                "message_start",
                {
                    "conversation_id": payload.conversation_id,
                    "message_id": user_message.id,
                    "runtime_execution_id": execution.id,
                    "runtime_execution_ids": trace["runtime_execution_ids"],
                    "execution_trace": trace,
                    "artifact_summaries": trace["artifact_summaries"],
                    "sources": trace_sources,
                    "provider_connection_name": resolved.provider_connection.provider_connection_name,
                    "model_name": resolved.model_name,
                    **build_trace_response_metadata(trace),
                },
            )
            message_started = True
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

            if not route_desktop:
                assistant_content = normalize_repo_copilot_response(assistant_content, trace)

            assistant_message = Message(
                id=generate_message_id("assistant"),
                conversation_id=payload.conversation_id,
                runtime_execution_id=execution.id,
                role="assistant",
                content=assistant_content,
                sources_json=trace_sources,
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
                details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
            )
            yield sse_event(
                "finish",
                {
                    "message_id": assistant_message.id,
                    "content": assistant_content,
                    "sources": trace_sources,
                    "runtime_execution_id": execution.id,
                    "runtime_execution_ids": trace["runtime_execution_ids"],
                    "execution_trace": trace,
                    "artifact_summaries": trace["artifact_summaries"],
                    "usage": usage,
                    "provider_connection_name": resolved.provider_connection.provider_connection_name,
                    "model_name": resolved.model_name,
                    **build_trace_response_metadata(trace),
                },
            )
        except (ProviderConfigurationError, OpenAIError) as exc:
            trace = trace or (
                await collect_desktop_operator_trace(
                    session,
                    workspace=workspace,
                    user=user,
                    conversation=conversation,
                    parent_execution=execution,
                    prompt=payload.content,
                    mode=payload.mode,
                    knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
                )
                if route_desktop
                else await collect_repo_copilot_trace(
                    session,
                    workspace=workspace,
                    user=user,
                    conversation=conversation,
                    parent_execution=execution,
                    prompt=payload.content,
                    mode=payload.mode,
                    knowledge_sources=retrieved_knowledge.sources if retrieved_knowledge else None,
                )
            )
            if route_desktop and isinstance(trace, dict):
                _, trace = await sync_operator_plan_from_trace(
                    session,
                    workspace_id=workspace.id,
                    created_by_id=user.id,
                    requested_prompt=payload.content,
                    trace=trace,
                    parent_execution_id=execution.id,
                    conversation_id=conversation.id,
                )
            fallback_content = (
                build_desktop_trace_fallback_content(trace, exc)
                if route_desktop
                else build_trace_fallback_content(trace, exc)
            )
            assistant_message = Message(
                id=generate_message_id("assistant"),
                conversation_id=payload.conversation_id,
                runtime_execution_id=execution.id,
                role="assistant",
                content=fallback_content,
                sources_json=trace_sources,
            )
            session.add(assistant_message)
            await session.commit()
            await session.refresh(assistant_message)
            await mark_runtime_succeeded(
                session,
                execution,
                response_preview=fallback_content[:400],
                details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
            )
            if not message_started:
                yield sse_event(
                    "message_start",
                    {
                        "conversation_id": payload.conversation_id,
                        "message_id": user_message.id,
                        "runtime_execution_id": execution.id,
                        "runtime_execution_ids": trace["runtime_execution_ids"],
                        "execution_trace": trace,
                        "artifact_summaries": trace["artifact_summaries"],
                        "sources": trace_sources,
                        "provider_connection_name": conversation.provider_connection.provider_connection_name if conversation.provider_connection else "Fallback",
                        "model_name": conversation.model_name or "deterministic",
                        **build_trace_response_metadata(trace),
                    },
                )
            yield sse_event(
                "finish",
                {
                    "message_id": assistant_message.id,
                    "content": fallback_content,
                    "sources": trace_sources,
                    "runtime_execution_id": execution.id,
                    "runtime_execution_ids": trace["runtime_execution_ids"],
                    "execution_trace": trace,
                    "artifact_summaries": trace["artifact_summaries"],
                    "usage": usage,
                    "provider_connection_name": conversation.provider_connection.provider_connection_name if conversation.provider_connection else "Fallback",
                    "model_name": conversation.model_name or "deterministic",
                    **build_trace_response_metadata(trace),
                },
            )
        except Exception as exc:
            await mark_runtime_failed(
                session,
                execution,
                error_message=str(exc),
                details_json=merge_runtime_details(summarize_details(retrieved_knowledge), trace),
            )
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
