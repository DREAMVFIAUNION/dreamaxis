from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import set_json
from app.models.runtime_execution import RuntimeExecution
from app.models.runtime_session import RuntimeSession
from app.models.runtime_session_event import RuntimeSessionEvent
from app.services.assistant_service import generate_entity_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_runtime_execution(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_id: str,
    source: str,
    execution_kind: str,
    provider_id: str | None,
    model_id: str | None,
    provider_connection_id: str | None = None,
    resolved_model_name: str | None = None,
    resolved_base_url: str | None = None,
    conversation_id: str | None = None,
    skill_id: str | None = None,
    runtime_id: str | None = None,
    runtime_session_id: str | None = None,
    prompt_preview: str | None = None,
    command_preview: str | None = None,
    details_json: dict[str, Any] | None = None,
    artifacts_json: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> RuntimeExecution:
    execution = RuntimeExecution(
        id=generate_entity_id("runtime"),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        skill_id=skill_id,
        runtime_id=runtime_id,
        runtime_session_id=runtime_session_id,
        provider_id=provider_id,
        model_id=model_id,
        provider_connection_id=provider_connection_id,
        user_id=user_id,
        source=source,
        execution_kind=execution_kind,
        status="queued",
        prompt_preview=prompt_preview,
        command_preview=command_preview,
        resolved_model_name=resolved_model_name,
        resolved_base_url=resolved_base_url,
        details_json=details_json,
        artifacts_json=artifacts_json,
        started_at=utcnow(),
    )
    session.add(execution)
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


async def update_runtime_binding(
    session: AsyncSession,
    execution: RuntimeExecution,
    *,
    runtime_id: str | None,
    runtime_session_id: str | None,
    command_preview: str | None = None,
) -> RuntimeExecution:
    execution.runtime_id = runtime_id
    execution.runtime_session_id = runtime_session_id
    if command_preview is not None:
        execution.command_preview = command_preview
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


async def mark_runtime_running(session: AsyncSession, execution: RuntimeExecution) -> RuntimeExecution:
    execution.status = "running"
    execution.started_at = execution.started_at or utcnow()
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


async def mark_runtime_succeeded(
    session: AsyncSession,
    execution: RuntimeExecution,
    *,
    response_preview: str | None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    details_json: dict[str, Any] | None = None,
    artifacts_json: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> RuntimeExecution:
    execution.status = "succeeded"
    execution.response_preview = response_preview
    execution.prompt_tokens = prompt_tokens
    execution.completion_tokens = completion_tokens
    execution.total_tokens = total_tokens
    execution.completed_at = utcnow()
    if execution.started_at and execution.completed_at:
        execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
    if details_json is not None:
        execution.details_json = details_json
    if artifacts_json is not None:
        execution.artifacts_json = artifacts_json
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


async def mark_runtime_failed(
    session: AsyncSession,
    execution: RuntimeExecution,
    *,
    error_message: str,
    details_json: dict[str, Any] | None = None,
    artifacts_json: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> RuntimeExecution:
    execution.status = "failed"
    execution.error_message = error_message
    execution.completed_at = utcnow()
    if execution.started_at and execution.completed_at:
        execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
    if details_json is not None:
        execution.details_json = details_json
    if artifacts_json is not None:
        execution.artifacts_json = artifacts_json
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


async def create_runtime_session_event(
    session: AsyncSession,
    *,
    runtime_session_id: str,
    event_type: str,
    message: str | None = None,
    payload_json: dict[str, Any] | None = None,
) -> RuntimeSessionEvent:
    event = RuntimeSessionEvent(
        id=generate_entity_id("rsevt"),
        runtime_session_id=runtime_session_id,
        event_type=event_type,
        message=message,
        payload_json=payload_json,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def touch_runtime_session(
    session: AsyncSession,
    runtime_session: RuntimeSession,
    *,
    status: str | None = None,
    context_json: dict[str, Any] | None = None,
) -> RuntimeSession:
    runtime_session.last_activity_at = utcnow()
    if status is not None:
        runtime_session.status = status
    if context_json is not None:
        runtime_session.context_json = context_json
    await session.commit()
    await session.refresh(runtime_session)
    return runtime_session


async def publish_runtime_state(execution: RuntimeExecution) -> None:
    payload = json.dumps(
        {
            "id": execution.id,
            "status": execution.status,
            "workspace_id": execution.workspace_id,
            "conversation_id": execution.conversation_id,
            "skill_id": execution.skill_id,
            "runtime_id": execution.runtime_id,
            "runtime_session_id": execution.runtime_session_id,
            "provider_id": execution.provider_id,
            "model_id": execution.model_id,
            "provider_connection_id": execution.provider_connection_id,
            "resolved_model_name": execution.resolved_model_name,
            "resolved_base_url": execution.resolved_base_url,
            "command_preview": execution.command_preview,
            "error_message": execution.error_message,
            "duration_ms": execution.duration_ms,
        }
    )
    await set_json(f"runtime:{execution.id}", payload)
