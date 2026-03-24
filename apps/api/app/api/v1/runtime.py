from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.agent_role import AgentRole
from app.models.runtime_execution import RuntimeExecution
from app.models.runtime_host import RuntimeHost
from app.models.runtime_session import RuntimeSession
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.runtime import (
    AgentRoleOut,
    BrowserExecutionResult,
    CliExecutionResult,
    DesktopApprovalReviewPayload,
    DesktopApprovalReviewResult,
    ExecutionAnnotationOut,
    RuntimeHeartbeatPayload,
    RuntimeExecutionOut,
    RuntimeHostOut,
    RuntimeHostRegisterPayload,
    RuntimeSessionCreate,
    RuntimeSessionEventOut,
    RuntimeSessionOut,
)
from app.services.desktop_operator import review_desktop_action_approval
from app.services.execution_annotations import derive_execution_timeline, summarize_execution_timeline, timeline_from_events
from app.services.runtime_dispatcher import (
    close_cli_session,
    create_cli_session,
    dispatch_browser_execution,
    dispatch_cli_execution,
    get_runtime_session_or_404,
)
from app.services.runtime_registry import get_online_runtime_for_workspace, heartbeat_runtime_host, list_runtimes_for_workspace, upsert_runtime_host
from app.services.runtime_service import mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded

router = APIRouter()
settings = get_settings()


def require_runtime_token(x_runtime_token: Annotated[str | None, Header()] = None) -> str:
    if not x_runtime_token or x_runtime_token != settings.RUNTIME_SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid runtime token")
    return x_runtime_token


def serialize_runtime_host(runtime: RuntimeHost) -> dict:
    return RuntimeHostOut.model_validate(runtime).model_dump()


def serialize_runtime_session(runtime_session: RuntimeSession) -> dict:
    return RuntimeSessionOut.model_validate(runtime_session).model_dump()


def serialize_runtime_execution(execution: RuntimeExecution) -> dict:
    details = execution.details_json or {}
    trace_summary = details.get("trace_summary") if isinstance(details, dict) else None
    if not trace_summary and isinstance(details, dict):
        execution_trace = details.get("execution_trace")
        if isinstance(execution_trace, dict):
            trace_summary = execution_trace.get("trace_summary")
    payload = RuntimeExecutionOut.model_validate(execution).model_dump()
    if trace_summary:
        payload["trace_summary"] = trace_summary
    else:
        payload["trace_summary"] = summarize_execution_timeline(execution, [])
    if isinstance(details, dict):
        payload["execution_bundle_id"] = details.get("execution_bundle_id")
        payload["parent_execution_id"] = details.get("parent_execution_id")
        payload["child_execution_ids"] = details.get("child_execution_ids")
        payload["mode"] = details.get("mode")
    return payload


@router.get("/runtimes")
async def list_runtimes(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
    runtime_type: str | None = Query(default=None),
):
    if workspace_id:
        workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user.id))
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        runtimes = await list_runtimes_for_workspace(session, workspace.id)
        if runtime_type:
            runtimes = [item for item in runtimes if item.runtime_type == runtime_type]
        return paginated_response([serialize_runtime_host(item) for item in runtimes])

    result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.created_at.asc()))
    workspaces = result.scalars().all()
    items: list[dict] = []
    for workspace in workspaces:
        workspace_runtimes = await list_runtimes_for_workspace(session, workspace.id)
        if runtime_type:
            workspace_runtimes = [runtime for runtime in workspace_runtimes if runtime.runtime_type == runtime_type]
        items.extend(serialize_runtime_host(runtime) for runtime in workspace_runtimes)
    return paginated_response(items)


@router.post("/runtimes/register")
async def register_runtime(
    payload: RuntimeHostRegisterPayload,
    _: Annotated[str, Depends(require_runtime_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    runtime = await upsert_runtime_host(
        session,
        runtime_id=payload.id,
        name=payload.name,
        runtime_type=payload.runtime_type,
        endpoint_url=payload.endpoint_url,
        capabilities_json=payload.capabilities_json,
        scope_type=payload.scope_type,
        scope_ref_id=payload.scope_ref_id,
    )
    return success_response(serialize_runtime_host(runtime))


@router.post("/runtimes/{runtime_id}/heartbeat")
async def runtime_heartbeat(
    runtime_id: str,
    _: Annotated[str, Depends(require_runtime_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
    payload: RuntimeHeartbeatPayload | None = None,
):
    runtime = await heartbeat_runtime_host(session, runtime_id, capabilities_json=payload.capabilities_json if payload else None)
    return success_response(serialize_runtime_host(runtime))


@router.get("/runtime-sessions")
async def list_runtime_sessions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
    session_type: str | None = Query(default=None),
):
    statement = (
        select(RuntimeSession)
        .options(selectinload(RuntimeSession.runtime))
        .join(Workspace, RuntimeSession.workspace_id == Workspace.id)
        .where(Workspace.owner_id == user.id)
    )
    if workspace_id:
        statement = statement.where(RuntimeSession.workspace_id == workspace_id)
    if session_type:
        statement = statement.where(RuntimeSession.session_type == session_type)
    result = await session.execute(statement.order_by(RuntimeSession.updated_at.desc()))
    return paginated_response([serialize_runtime_session(item) for item in result.scalars().all()])


@router.get("/runtime-sessions/{runtime_session_id}/events")
async def list_runtime_session_events(
    runtime_session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    runtime_session = await get_runtime_session_or_404(session, runtime_session_id=runtime_session_id, user_id=user.id)
    await session.refresh(runtime_session, attribute_names=["events"])
    items = [RuntimeSessionEventOut.model_validate(item).model_dump() for item in sorted(runtime_session.events, key=lambda event: event.created_at)]
    return paginated_response(items)


@router.post("/runtime-sessions")
async def create_runtime_session(
    payload: RuntimeSessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = await session.scalar(select(Workspace).where(Workspace.id == payload.workspace_id, Workspace.owner_id == user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

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
        session_mode="reuse" if payload.reusable else "new",
        working_directory=payload.working_directory,
    )
    return success_response(serialize_runtime_session(runtime_session))


@router.post("/runtime-sessions/{runtime_session_id}/close")
async def close_runtime_session(
    runtime_session_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    runtime_session = await get_runtime_session_or_404(session, runtime_session_id=runtime_session_id, user_id=user.id)
    runtime_session = await close_cli_session(session, runtime_session)
    return success_response(serialize_runtime_session(runtime_session))


@router.get("/runtime-executions")
async def list_runtime_executions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
):
    statement = (
        select(RuntimeExecution)
        .options(
            selectinload(RuntimeExecution.provider_connection),
            selectinload(RuntimeExecution.runtime),
            selectinload(RuntimeExecution.runtime_session),
        )
        .where(RuntimeExecution.user_id == user.id)
    )
    if workspace_id:
        statement = statement.where(RuntimeExecution.workspace_id == workspace_id)
    if conversation_id:
        statement = statement.where(RuntimeExecution.conversation_id == conversation_id)
    result = await session.execute(statement.order_by(RuntimeExecution.created_at.desc()))
    items = [serialize_runtime_execution(item) for item in result.scalars().all()]
    return paginated_response(items)


@router.get("/runtime-executions/{execution_id}")
async def get_runtime_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(RuntimeExecution)
        .options(
            selectinload(RuntimeExecution.provider_connection),
            selectinload(RuntimeExecution.runtime),
            selectinload(RuntimeExecution.runtime_session),
            selectinload(RuntimeExecution.skill),
        )
        .where(RuntimeExecution.id == execution_id, RuntimeExecution.user_id == user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Runtime execution not found")
    return success_response(serialize_runtime_execution(execution))


@router.get("/runtime-executions/{execution_id}/timeline")
async def get_runtime_execution_timeline(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(RuntimeExecution)
        .options(selectinload(RuntimeExecution.runtime_session).selectinload(RuntimeSession.events))
        .where(RuntimeExecution.id == execution_id, RuntimeExecution.user_id == user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Runtime execution not found")
    runtime_session = execution.runtime_session
    session_events = runtime_session.events if runtime_session else []
    timeline = derive_execution_timeline(execution, session_events=session_events)
    return success_response(
        {
            "execution_id": execution.id,
            "trace_summary": summarize_execution_timeline(execution, timeline),
            "timeline": [ExecutionAnnotationOut.model_validate(item).model_dump() for item in timeline],
        }
    )


@router.post("/runtime-executions/{execution_id}/desktop-approval")
async def review_runtime_execution_desktop_approval(
    execution_id: str,
    payload: DesktopApprovalReviewPayload,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(RuntimeExecution)
        .options(
            selectinload(RuntimeExecution.provider_connection),
            selectinload(RuntimeExecution.runtime),
            selectinload(RuntimeExecution.runtime_session),
        )
        .join(Workspace, RuntimeExecution.workspace_id == Workspace.id)
        .where(RuntimeExecution.id == execution_id, Workspace.owner_id == user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Runtime execution not found")

    workspace = await session.scalar(select(Workspace).where(Workspace.id == execution.workspace_id, Workspace.owner_id == user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    try:
        parent_execution, child_execution, trace = await review_desktop_action_approval(
            session,
            workspace=workspace,
            user=user,
            parent_execution=execution,
            decision=payload.decision,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success_response(
        DesktopApprovalReviewResult(
            execution=serialize_runtime_execution(parent_execution),
            child_execution=serialize_runtime_execution(child_execution) if child_execution else None,
            execution_trace=trace,
        ).model_dump()
    )


@router.get("/logs/events")
async def list_log_events(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
    runtime_type: str | None = Query(default=None),
    execution_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
):
    statement = (
        select(RuntimeSession)
        .options(selectinload(RuntimeSession.events), selectinload(RuntimeSession.runtime))
        .join(Workspace, RuntimeSession.workspace_id == Workspace.id)
        .where(Workspace.owner_id == user.id)
    )
    if workspace_id:
        statement = statement.where(RuntimeSession.workspace_id == workspace_id)
    if session_id:
        statement = statement.where(RuntimeSession.id == session_id)
    result = await session.execute(statement.order_by(RuntimeSession.updated_at.desc()))
    sessions = result.scalars().all()
    items: list[dict] = []
    for runtime_session in sessions:
        if runtime_type and runtime_session.runtime and runtime_session.runtime.runtime_type != runtime_type:
            continue
        for item in timeline_from_events(list(runtime_session.events), runtime_execution_id=execution_id):
            if kind and item.get("kind") != kind:
                continue
            items.append(item)
    items.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return paginated_response([ExecutionAnnotationOut.model_validate(item).model_dump() for item in items])


@router.post("/runtime-executions/{execution_id}/dispatch-cli")
async def dispatch_cli_runtime_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(RuntimeExecution)
        .options(selectinload(RuntimeExecution.skill))
        .join(Workspace, RuntimeExecution.workspace_id == Workspace.id)
        .where(RuntimeExecution.id == execution_id, Workspace.owner_id == user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Runtime execution not found")
    if not execution.skill or execution.skill.skill_mode != "cli":
        raise HTTPException(status_code=400, detail="Execution is not bound to a CLI skill")
    if not execution.command_preview:
        raise HTTPException(status_code=400, detail="Execution does not have a command preview to dispatch")

    workspace = await session.scalar(select(Workspace).where(Workspace.id == execution.workspace_id, Workspace.owner_id == user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    await mark_runtime_running(session, execution)
    try:
        result = await dispatch_cli_execution(
            session,
            workspace=workspace,
            user=user,
            execution=execution,
            skill=execution.skill,
            command=execution.command_preview,
        )
        details = {
            "exit_code": result.get("exit_code"),
            "stderr": (result.get("stderr") or "")[:2000],
            "cwd": result.get("cwd"),
        }
        if int(result.get("exit_code") or 0) == 0:
            await mark_runtime_succeeded(
                session,
                execution,
                response_preview=(result.get("stdout") or result.get("stderr") or "")[:2000],
                details_json=details,
                artifacts_json=result.get("artifacts_json"),
            )
        else:
            await mark_runtime_failed(
                session,
                execution,
                error_message=(result.get("stderr") or result.get("stdout") or "CLI command failed"),
                details_json=details,
                artifacts_json=result.get("artifacts_json"),
            )
        return success_response(CliExecutionResult.model_validate(result).model_dump())
    except Exception as exc:
        await mark_runtime_failed(session, execution, error_message=str(exc))
        raise


@router.post("/runtime-executions/{execution_id}/dispatch-browser")
async def dispatch_browser_runtime_execution(
    execution_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await session.scalar(
        select(RuntimeExecution)
        .options(selectinload(RuntimeExecution.skill))
        .join(Workspace, RuntimeExecution.workspace_id == Workspace.id)
        .where(RuntimeExecution.id == execution_id, Workspace.owner_id == user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Runtime execution not found")
    if not execution.skill or execution.skill.skill_mode != "browser":
        raise HTTPException(status_code=400, detail="Execution is not bound to a browser skill")
    if not execution.command_preview:
        raise HTTPException(status_code=400, detail="Execution does not have a browser action payload to dispatch")

    workspace = await session.scalar(select(Workspace).where(Workspace.id == execution.workspace_id, Workspace.owner_id == user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    await mark_runtime_running(session, execution)
    try:
        import json

        result = await dispatch_browser_execution(
            session,
            workspace=workspace,
            user=user,
            execution=execution,
            skill=execution.skill,
            actions=json.loads(execution.command_preview),
        )
        response_preview = (result.get("extracted_text") or result.get("title") or result.get("current_url") or "")[:2000]
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=response_preview,
            details_json={
                "current_url": result.get("current_url"),
                "title": result.get("title"),
            },
            artifacts_json=result.get("artifacts_json"),
        )
        return success_response(BrowserExecutionResult.model_validate(result).model_dump())
    except Exception as exc:
        await mark_runtime_failed(session, execution, error_message=str(exc))
        raise


@router.get("/agent-roles")
async def list_agent_roles(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    result = await session.execute(select(AgentRole).order_by(AgentRole.created_at.asc()))
    items = [AgentRoleOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)
