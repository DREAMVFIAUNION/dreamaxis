from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.runtime_execution import RuntimeExecution
from app.models.runtime_host import RuntimeHost
from app.models.runtime_session import RuntimeSession
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace
from app.services.assistant_service import generate_entity_id
from app.services.runtime_policy import (
    DESKTOP_READ_ONLY_ACTIONS,
    ensure_runtime_type,
    resolve_workspace_path,
    validate_browser_actions,
    validate_cli_command,
    validate_desktop_actions,
)
from app.services.runtime_registry import get_online_runtime_for_workspace
from app.services.runtime_service import create_runtime_session_event, touch_runtime_session, update_runtime_binding

settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def render_template(template: str, variables: dict[str, str] | None) -> str:
    values = variables or {}

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = values.get(key)
        return "" if value is None else str(value)

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", replace, template)


def _build_headers() -> dict[str, str]:
    return {"X-Runtime-Token": settings.RUNTIME_SHARED_TOKEN}


async def _worker_request(method: str, url: str, *, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=settings.RUNTIME_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.request(method, url, json=json_payload, headers=_build_headers())
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Runtime worker request failed: {response.text}")
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def build_cli_session_context(workspace_root: str, working_directory: str | None, shell: str) -> dict[str, Any]:
    cwd = str(resolve_workspace_path(workspace_root, working_directory))
    repo_root = str(resolve_workspace_path(workspace_root, None))
    return {
        "cwd": cwd,
        "shell": shell,
        "env_whitelist": ["PATH", "HOME", "USERPROFILE", "TEMP", "TMP"],
        "repo_root": repo_root,
        "last_command_at": None,
    }


def build_browser_session_context() -> dict[str, Any]:
    return {
        "current_url": None,
        "title": None,
        "tabs": [],
        "last_action_at": None,
    }


def build_desktop_session_context() -> dict[str, Any]:
    return {
        "focused_window": None,
        "last_action_at": None,
        "last_screenshot_at": None,
        "pending_approval": None,
    }


async def get_reusable_session(
    session: AsyncSession,
    *,
    runtime_id: str,
    workspace_id: str,
    session_type: str,
    cwd: str | None = None,
) -> RuntimeSession | None:
    result = await session.execute(
        select(RuntimeSession)
        .where(
            RuntimeSession.runtime_id == runtime_id,
            RuntimeSession.workspace_id == workspace_id,
            RuntimeSession.session_type == session_type,
            RuntimeSession.reusable.is_(True),
            RuntimeSession.status.in_(["idle", "busy"]),
        )
        .order_by(RuntimeSession.updated_at.desc())
    )
    for runtime_session in result.scalars().all():
        if session_type == "cli":
            if (runtime_session.context_json or {}).get("cwd") == cwd:
                return runtime_session
        else:
            return runtime_session
    return None


async def create_cli_session(
    session: AsyncSession,
    *,
    runtime: RuntimeHost,
    workspace: Workspace,
    user: User,
    session_mode: str,
    working_directory: str | None,
) -> RuntimeSession:
    shell = ((runtime.capabilities_json or {}).get("shell") or "powershell")
    context = build_cli_session_context(workspace.workspace_root_path or str(settings.workspace_root_base_dir), working_directory, shell)
    if session_mode == "reuse":
        reusable = await get_reusable_session(
            session,
            runtime_id=runtime.id,
            workspace_id=workspace.id,
            session_type="cli",
            cwd=context["cwd"],
        )
        if reusable:
            return reusable

    runtime_session = RuntimeSession(
        id=generate_entity_id("session"),
        session_type="cli",
        runtime_id=runtime.id,
        workspace_id=workspace.id,
        created_by_id=user.id,
        status="idle",
        reusable=session_mode == "reuse",
        context_json=context,
        last_activity_at=utcnow(),
    )
    session.add(runtime_session)
    await session.commit()
    await session.refresh(runtime_session)

    try:
        await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions",
            json_payload={
                "session_id": runtime_session.id,
                "workspace_id": workspace.id,
                "session_type": runtime_session.session_type,
                "reusable": runtime_session.reusable,
                "context_json": runtime_session.context_json,
            },
        )
        await create_runtime_session_event(
            session,
            runtime_session_id=runtime_session.id,
            event_type="session_created",
            message="CLI session created",
            annotation_kind="session_created",
            annotation_title="CLI session created",
            annotation_summary="Created a reusable CLI session for workspace-bound command execution.",
            annotation_status="ready",
            source_layer="runtime",
            target_label=context.get("cwd"),
            payload_preview={"cwd": context.get("cwd"), "reusable": runtime_session.reusable},
            payload_json={"runtime_id": runtime.id, "context_json": runtime_session.context_json},
        )
        return runtime_session
    except Exception:
        runtime_session.status = "error"
        await session.commit()
        raise


async def create_browser_session(
    session: AsyncSession,
    *,
    runtime: RuntimeHost,
    workspace: Workspace,
    user: User,
    session_mode: str,
) -> RuntimeSession:
    context = build_browser_session_context()
    if session_mode == "reuse":
        reusable = await get_reusable_session(
            session,
            runtime_id=runtime.id,
            workspace_id=workspace.id,
            session_type="browser",
        )
        if reusable:
            return reusable

    runtime_session = RuntimeSession(
        id=generate_entity_id("session"),
        session_type="browser",
        runtime_id=runtime.id,
        workspace_id=workspace.id,
        created_by_id=user.id,
        status="idle",
        reusable=session_mode == "reuse",
        context_json=context,
        last_activity_at=utcnow(),
    )
    session.add(runtime_session)
    await session.commit()
    await session.refresh(runtime_session)

    try:
        await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions",
            json_payload={
                "session_id": runtime_session.id,
                "workspace_id": workspace.id,
                "session_type": runtime_session.session_type,
                "reusable": runtime_session.reusable,
                "context_json": runtime_session.context_json,
            },
        )
        await create_runtime_session_event(
            session,
            runtime_session_id=runtime_session.id,
            event_type="session_created",
            message="Browser session created",
            annotation_kind="session_created",
            annotation_title="Browser session created",
            annotation_summary="Created a reusable browser session for local page automation.",
            annotation_status="ready",
            source_layer="runtime",
            payload_preview={"reusable": runtime_session.reusable},
            payload_json={"runtime_id": runtime.id, "context_json": runtime_session.context_json},
        )
        return runtime_session
    except Exception:
        runtime_session.status = "error"
        await session.commit()
        raise


async def create_desktop_session(
    session: AsyncSession,
    *,
    runtime: RuntimeHost,
    workspace: Workspace,
    user: User,
    session_mode: str,
) -> RuntimeSession:
    context = build_desktop_session_context()
    if session_mode == "reuse":
        reusable = await get_reusable_session(
            session,
            runtime_id=runtime.id,
            workspace_id=workspace.id,
            session_type="desktop",
        )
        if reusable:
            return reusable

    runtime_session = RuntimeSession(
        id=generate_entity_id("session"),
        session_type="desktop",
        runtime_id=runtime.id,
        workspace_id=workspace.id,
        created_by_id=user.id,
        status="idle",
        reusable=session_mode == "reuse",
        context_json=context,
        last_activity_at=utcnow(),
    )
    session.add(runtime_session)
    await session.commit()
    await session.refresh(runtime_session)

    try:
        await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions",
            json_payload={
                "session_id": runtime_session.id,
                "workspace_id": workspace.id,
                "session_type": runtime_session.session_type,
                "reusable": runtime_session.reusable,
                "context_json": runtime_session.context_json,
            },
        )
        await create_runtime_session_event(
            session,
            runtime_session_id=runtime_session.id,
            event_type="session_created",
            message="Desktop session created",
            annotation_kind="session_created",
            annotation_title="Desktop session created",
            annotation_summary="Created a reusable desktop session for Windows inspection or gated control.",
            annotation_status="ready",
            source_layer="runtime",
            payload_preview={"reusable": runtime_session.reusable},
            payload_json={"runtime_id": runtime.id, "context_json": runtime_session.context_json},
        )
        return runtime_session
    except Exception:
        runtime_session.status = "error"
        await session.commit()
        raise


async def close_cli_session(session: AsyncSession, runtime_session: RuntimeSession, runtime: RuntimeHost | None = None) -> RuntimeSession:
    runtime = runtime or runtime_session.runtime
    if runtime:
        await _worker_request("POST", f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/close")
    runtime_session.status = "closed"
    runtime_session.last_activity_at = utcnow()
    await session.commit()
    await session.refresh(runtime_session)
    await create_runtime_session_event(
        session,
        runtime_session_id=runtime_session.id,
        event_type="session_closed",
        message="Runtime session closed",
        annotation_kind="session_closed",
        annotation_title="Session closed",
        annotation_summary="Closed the runtime session and released its active context.",
        annotation_status="ready",
        source_layer="runtime",
        payload_json={"runtime_id": runtime_session.runtime_id},
    )
    return runtime_session


async def dispatch_cli_execution(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    execution: RuntimeExecution,
    skill: SkillDefinition,
    command: str,
    working_directory: str | None = None,
) -> dict[str, Any]:
    ensure_runtime_type(skill.required_runtime_type, "cli")
    normalized_command = validate_cli_command(command)
    runtime = await get_online_runtime_for_workspace(
        session,
        workspace.id,
        "cli",
        workspace.workspace_root_path,
    )
    runtime_session = await create_cli_session(
        session,
        runtime=runtime,
        workspace=workspace,
        user=user,
        session_mode=skill.session_mode or "reuse",
        working_directory=working_directory if working_directory is not None else skill.working_directory,
    )
    await update_runtime_binding(
        session,
        execution,
        runtime_id=runtime.id,
        runtime_session_id=runtime_session.id,
        command_preview=normalized_command,
    )

    try:
        result = await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
            json_payload={
                "command": normalized_command,
                "cwd": (runtime_session.context_json or {}).get("cwd"),
            },
        )
    except HTTPException as exc:
        if "CLI session not found" in str(exc.detail):
            runtime_session.status = "closed"
            await session.commit()
            runtime_session = await create_cli_session(
                session,
                runtime=runtime,
                workspace=workspace,
                user=user,
                session_mode="new",
                working_directory=working_directory if working_directory is not None else skill.working_directory,
            )
            await update_runtime_binding(
                session,
                execution,
                runtime_id=runtime.id,
                runtime_session_id=runtime_session.id,
                command_preview=normalized_command,
            )
            result = await _worker_request(
                "POST",
                f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
                json_payload={
                    "command": normalized_command,
                    "cwd": (runtime_session.context_json or {}).get("cwd"),
                },
            )
        else:
            if runtime_session.status != "closed":
                runtime_session.status = "error"
                await session.commit()
            raise exc

    updated_context = {
        **(runtime_session.context_json or {}),
        "cwd": result.get("cwd") or (runtime_session.context_json or {}).get("cwd"),
        "last_command_at": utcnow().isoformat(),
    }
    await touch_runtime_session(session, runtime_session, status="idle", context_json=updated_context)
    await create_runtime_session_event(
        session,
        runtime_session_id=runtime_session.id,
        event_type="command_executed",
        execution_id=execution.id,
        message="CLI command executed",
        annotation_kind="command_finished",
        annotation_title="CLI command executed",
        annotation_summary=f"Ran a workspace-scoped command with exit code {result.get('exit_code')}.",
        annotation_status="succeeded" if int(result.get("exit_code") or 0) == 0 else "failed",
        source_layer="runtime",
        target_label=normalized_command[:120],
        duration_ms=result.get("duration_ms"),
        payload_preview={
            "command": normalized_command,
            "exit_code": result.get("exit_code"),
            "cwd": result.get("cwd"),
        },
        payload_json={
            "command": normalized_command,
            "exit_code": result.get("exit_code"),
            "duration_ms": result.get("duration_ms"),
            "cwd": result.get("cwd"),
        },
    )
    return {
        **result,
        "runtime_id": runtime.id,
        "runtime_session_id": runtime_session.id,
        "command": normalized_command,
    }


async def dispatch_browser_execution(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    execution: RuntimeExecution,
    skill: SkillDefinition,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    ensure_runtime_type(skill.required_runtime_type, "browser")
    normalized_actions = validate_browser_actions(actions)
    runtime = await get_online_runtime_for_workspace(
        session,
        workspace.id,
        "browser",
        workspace.workspace_root_path,
    )
    runtime_session = await create_browser_session(
        session,
        runtime=runtime,
        workspace=workspace,
        user=user,
        session_mode=skill.session_mode or "reuse",
    )
    await update_runtime_binding(
        session,
        execution,
        runtime_id=runtime.id,
        runtime_session_id=runtime_session.id,
        command_preview=json.dumps(normalized_actions),
    )

    try:
        result = await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
            json_payload={"actions": normalized_actions},
        )
    except HTTPException as exc:
        if "Browser session not found" in str(exc.detail):
            runtime_session.status = "closed"
            await session.commit()
            runtime_session = await create_browser_session(
                session,
                runtime=runtime,
                workspace=workspace,
                user=user,
                session_mode="new",
            )
            await update_runtime_binding(
                session,
                execution,
                runtime_id=runtime.id,
                runtime_session_id=runtime_session.id,
                command_preview=json.dumps(normalized_actions),
            )
            result = await _worker_request(
                "POST",
                f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
                json_payload={"actions": normalized_actions},
            )
        else:
            if runtime_session.status != "closed":
                runtime_session.status = "error"
                await session.commit()
            raise exc

    updated_context = {
        **(runtime_session.context_json or {}),
        "current_url": result.get("current_url"),
        "title": result.get("title"),
        "last_action_at": utcnow().isoformat(),
    }
    await touch_runtime_session(session, runtime_session, status="idle", context_json=updated_context)
    await create_runtime_session_event(
        session,
        runtime_session_id=runtime_session.id,
        event_type="browser_actions_executed",
        execution_id=execution.id,
        message="Browser actions executed",
        annotation_kind="browser_action",
        annotation_title="Browser actions executed",
        annotation_summary="Ran browser automation actions and captured the resulting page state.",
        annotation_status="succeeded",
        source_layer="runtime",
        target_label=result.get("current_url"),
        duration_ms=result.get("duration_ms"),
        payload_preview={
            "actions": normalized_actions[:3],
            "current_url": result.get("current_url"),
            "title": result.get("title"),
        },
        payload_json={
            "actions": normalized_actions,
            "duration_ms": result.get("duration_ms"),
            "current_url": result.get("current_url"),
            "title": result.get("title"),
        },
    )
    return {
        **result,
        "runtime_id": runtime.id,
        "runtime_session_id": runtime_session.id,
        "actions": normalized_actions,
    }


async def dispatch_desktop_execution(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    execution: RuntimeExecution,
    actions: list[dict[str, Any]],
    session_mode: str = "reuse",
    require_read_only: bool = True,
) -> dict[str, Any]:
    normalized_actions = validate_desktop_actions(actions, require_read_only=require_read_only)
    runtime = await get_online_runtime_for_workspace(
        session,
        workspace.id,
        "desktop",
        workspace.workspace_root_path,
    )
    runtime_session = await create_desktop_session(
        session,
        runtime=runtime,
        workspace=workspace,
        user=user,
        session_mode=session_mode,
    )
    await update_runtime_binding(
        session,
        execution,
        runtime_id=runtime.id,
        runtime_session_id=runtime_session.id,
        command_preview=json.dumps(normalized_actions),
    )

    try:
        result = await _worker_request(
            "POST",
            f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
            json_payload={"actions": normalized_actions},
        )
    except HTTPException as exc:
        if "Desktop session not found" in str(exc.detail):
            runtime_session.status = "closed"
            await session.commit()
            runtime_session = await create_desktop_session(
                session,
                runtime=runtime,
                workspace=workspace,
                user=user,
                session_mode="new",
            )
            await update_runtime_binding(
                session,
                execution,
                runtime_id=runtime.id,
                runtime_session_id=runtime_session.id,
                command_preview=json.dumps(normalized_actions),
            )
            result = await _worker_request(
                "POST",
                f"{runtime.endpoint_url}/internal/runtime/sessions/{runtime_session.id}/execute",
                json_payload={"actions": normalized_actions},
            )
        else:
            if runtime_session.status != "closed":
                runtime_session.status = "error"
                await session.commit()
            raise exc

    updated_context = {
        **(runtime_session.context_json or {}),
        "focused_window": result.get("focused_window") or result.get("active_window"),
        "last_action_at": utcnow().isoformat(),
        "last_screenshot_at": utcnow().isoformat() if any(action.get("action") == "capture_screen" for action in normalized_actions) else (runtime_session.context_json or {}).get("last_screenshot_at"),
    }
    await touch_runtime_session(session, runtime_session, status="idle", context_json=updated_context)
    first_action = normalized_actions[0]["action"] if normalized_actions else "desktop"
    action_mode = "read-only" if all(action["action"] in DESKTOP_READ_ONLY_ACTIONS for action in normalized_actions) else "gated"
    await create_runtime_session_event(
        session,
        runtime_session_id=runtime_session.id,
        event_type="desktop_actions_executed",
        execution_id=execution.id,
        message="Desktop actions executed",
        annotation_kind="desktop_action",
        annotation_title="Desktop actions executed",
        annotation_summary=f"Ran {action_mode} desktop actions and captured the resulting Windows state.",
        annotation_status="succeeded",
        source_layer="runtime",
        target_label=str(result.get("active_window") or result.get("focused_window") or first_action),
        duration_ms=result.get("duration_ms"),
        payload_preview={
            "actions": normalized_actions[:3],
            "focused_window": result.get("focused_window") or result.get("active_window"),
            "artifact_count": len(result.get("artifacts_json") or []),
        },
        payload_json={
            "actions": normalized_actions,
            "duration_ms": result.get("duration_ms"),
            "focused_window": result.get("focused_window") or result.get("active_window"),
        },
    )
    return {
        **result,
        "runtime_id": runtime.id,
        "runtime_session_id": runtime_session.id,
        "actions": normalized_actions,
    }


async def get_runtime_session_or_404(
    session: AsyncSession,
    *,
    runtime_session_id: str,
    user_id: str,
) -> RuntimeSession:
    runtime_session = await session.scalar(
        select(RuntimeSession)
        .options(selectinload(RuntimeSession.runtime))
        .join(Workspace, RuntimeSession.workspace_id == Workspace.id)
        .where(RuntimeSession.id == runtime_session_id, Workspace.owner_id == user_id)
    )
    if not runtime_session:
        raise HTTPException(status_code=404, detail="Runtime session not found")
    return runtime_session
