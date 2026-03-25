from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import success_response
from app.models.conversation import Conversation
from app.models.operator_plan import OperatorPlan
from app.models.runtime_execution import RuntimeExecution
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.operator_plan import OperatorPlanActionReview, OperatorPlanCreate, OperatorPlanOut
from app.services.desktop_operator import collect_desktop_operator_trace, review_desktop_action_approval
from app.services.operator_plans import (
    get_operator_plan_or_404,
    list_builtin_operator_templates,
    resolve_operator_plan_input,
    sync_operator_plan_from_trace,
)
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded

router = APIRouter()


def _serialize_operator_plan(plan) -> dict[str, Any]:
    return OperatorPlanOut.model_validate(plan).model_dump()


def _merge_execution_details(trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": trace.get("mode"),
        "operator_plan_id": trace.get("operator_plan_id"),
        "operator_stage": trace.get("operator_stage"),
        "execution_bundle_id": trace.get("execution_bundle_id"),
        "child_execution_ids": trace.get("child_execution_ids") or [],
        "trace_summary": trace.get("trace_summary"),
        "execution_trace": trace,
        "artifact_summaries": trace.get("artifact_summaries") or [],
        "evidence_items": trace.get("evidence_items") or trace.get("evidence") or [],
        "recommended_next_actions": trace.get("recommended_next_actions") or [],
    }


async def _get_workspace_or_404(session: AsyncSession, *, workspace_id: str, user_id: str) -> Workspace:
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def _get_conversation_or_404(
    session: AsyncSession, *, conversation_id: str | None, workspace_id: str, user_id: str
) -> Conversation | None:
    if not conversation_id:
        return None
    conversation = await session.scalar(
        select(Conversation)
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Conversation.id == conversation_id, Conversation.workspace_id == workspace_id, Workspace.owner_id == user_id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/operator-plans")
async def list_operator_plans(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    statement = select(OperatorPlan).where(OperatorPlan.created_by_id == user.id)
    if workspace_id:
        statement = statement.where(OperatorPlan.workspace_id == workspace_id)
    result = await session.execute(statement.order_by(OperatorPlan.updated_at.desc()))
    items = [_serialize_operator_plan(item) for item in result.scalars().all()]
    return success_response({"items": items, "templates": list_builtin_operator_templates()})


@router.get("/operator-plans/{operator_plan_id}")
async def get_operator_plan(
    operator_plan_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    plan = await get_operator_plan_or_404(session, operator_plan_id=operator_plan_id, user_id=user.id)
    return success_response(_serialize_operator_plan(plan))


@router.post("/operator-plans")
async def create_operator_plan(
    payload: OperatorPlanCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = await _get_workspace_or_404(session, workspace_id=payload.workspace_id, user_id=user.id)
    conversation = await _get_conversation_or_404(
        session,
        conversation_id=payload.conversation_id,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    resolved_input = resolve_operator_plan_input(
        prompt=payload.prompt,
        mode=payload.mode,
        template_slug=payload.template_slug,
        title=payload.title,
    )
    parent_execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="chat",
        provider_id=conversation.provider_id if conversation else None,
        model_id=conversation.model_id if conversation else None,
        provider_connection_id=conversation.provider_connection_id if conversation else None,
        resolved_model_name=conversation.model_name if conversation else None,
        resolved_base_url=conversation.provider_connection.base_url if conversation and conversation.provider_connection else None,
        conversation_id=conversation.id if conversation else None,
        prompt_preview=resolved_input["prompt"][:400] if resolved_input["prompt"] else None,
        details_json={"requested_mode": resolved_input["mode"], "template_slug": resolved_input["template_slug"]},
    )

    trace: dict[str, Any] | None = None
    try:
        await mark_runtime_running(session, parent_execution)
        trace = await collect_desktop_operator_trace(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            parent_execution=parent_execution,
            prompt=resolved_input["prompt"] or "",
            mode=resolved_input["mode"],
        )
        plan, updated_trace = await sync_operator_plan_from_trace(
            session,
            workspace_id=workspace.id,
            created_by_id=user.id,
            requested_prompt=resolved_input["prompt"] or "",
            trace=trace,
            parent_execution_id=parent_execution.id,
            conversation_id=conversation.id if conversation else None,
            template_slug=resolved_input["template_slug"],
            title_override=resolved_input["title"],
        )
        await mark_runtime_succeeded(
            session,
            parent_execution,
            response_preview=str((updated_trace.get("trace_summary") or {}).get("summary") or resolved_input["title"] or "Operator plan created")[:400],
            details_json=_merge_execution_details(updated_trace),
            artifacts_json=updated_trace.get("artifact_summaries"),
        )
        return success_response(_serialize_operator_plan(plan))
    except Exception as exc:
        await mark_runtime_failed(
            session,
            parent_execution,
            error_message=str(exc),
            details_json=_merge_execution_details(trace or {"mode": resolved_input["mode"]}),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/operator-plans/{operator_plan_id}/approve")
async def approve_operator_plan(
    operator_plan_id: str,
    payload: OperatorPlanActionReview,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    if payload.decision != "approved":
        raise HTTPException(status_code=400, detail="Use the deny endpoint for denied actions.")
    plan = await get_operator_plan_or_404(session, operator_plan_id=operator_plan_id, user_id=user.id)
    if not plan.parent_execution_id:
        raise HTTPException(status_code=400, detail="Operator plan has no parent execution to approve.")
    workspace = await _get_workspace_or_404(session, workspace_id=plan.workspace_id, user_id=user.id)
    parent_execution = await session.scalar(select(RuntimeExecution).where(RuntimeExecution.id == plan.parent_execution_id))
    if not parent_execution:
        raise HTTPException(status_code=404, detail="Parent runtime execution not found")
    parent_execution, _, trace = await review_desktop_action_approval(
        session,
        workspace=workspace,
        user=user,
        parent_execution=parent_execution,
        decision="approved",
    )
    updated_plan, updated_trace = await sync_operator_plan_from_trace(
        session,
        workspace_id=plan.workspace_id,
        created_by_id=user.id,
        requested_prompt=plan.requested_prompt,
        trace=trace,
        parent_execution_id=parent_execution.id,
        conversation_id=plan.conversation_id,
        operator_plan_id=plan.id,
        template_slug=plan.template_slug,
        title_override=plan.title,
    )
    parent_execution.details_json = _merge_execution_details(updated_trace)
    await session.commit()
    return success_response(_serialize_operator_plan(updated_plan))


@router.post("/operator-plans/{operator_plan_id}/deny")
async def deny_operator_plan(
    operator_plan_id: str,
    payload: OperatorPlanActionReview,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    if payload.decision != "denied":
        raise HTTPException(status_code=400, detail="Use the approve endpoint for approved actions.")
    plan = await get_operator_plan_or_404(session, operator_plan_id=operator_plan_id, user_id=user.id)
    if not plan.parent_execution_id:
        raise HTTPException(status_code=400, detail="Operator plan has no parent execution to deny.")
    workspace = await _get_workspace_or_404(session, workspace_id=plan.workspace_id, user_id=user.id)
    parent_execution = await session.scalar(select(RuntimeExecution).where(RuntimeExecution.id == plan.parent_execution_id))
    if not parent_execution:
        raise HTTPException(status_code=404, detail="Parent runtime execution not found")
    parent_execution, _, trace = await review_desktop_action_approval(
        session,
        workspace=workspace,
        user=user,
        parent_execution=parent_execution,
        decision="denied",
    )
    updated_plan, updated_trace = await sync_operator_plan_from_trace(
        session,
        workspace_id=plan.workspace_id,
        created_by_id=user.id,
        requested_prompt=plan.requested_prompt,
        trace=trace,
        parent_execution_id=parent_execution.id,
        conversation_id=plan.conversation_id,
        operator_plan_id=plan.id,
        template_slug=plan.template_slug,
        title_override=plan.title,
    )
    parent_execution.details_json = _merge_execution_details(updated_trace)
    await session.commit()
    return success_response(_serialize_operator_plan(updated_plan))


@router.post("/operator-plans/{operator_plan_id}/resume")
async def resume_operator_plan(
    operator_plan_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    plan = await get_operator_plan_or_404(session, operator_plan_id=operator_plan_id, user_id=user.id)
    workspace = await _get_workspace_or_404(session, workspace_id=plan.workspace_id, user_id=user.id)
    conversation = await _get_conversation_or_404(
        session,
        conversation_id=plan.conversation_id,
        workspace_id=workspace.id,
        user_id=user.id,
    )
    parent_execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="chat",
        provider_id=conversation.provider_id if conversation else None,
        model_id=conversation.model_id if conversation else None,
        provider_connection_id=conversation.provider_connection_id if conversation else None,
        resolved_model_name=conversation.model_name if conversation else None,
        resolved_base_url=conversation.provider_connection.base_url if conversation and conversation.provider_connection else None,
        conversation_id=conversation.id if conversation else None,
        prompt_preview=plan.requested_prompt[:400],
        details_json={"requested_mode": plan.mode, "template_slug": plan.template_slug, "resumed_operator_plan_id": plan.id},
    )
    trace: dict[str, Any] | None = None
    try:
        await mark_runtime_running(session, parent_execution)
        trace = await collect_desktop_operator_trace(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            parent_execution=parent_execution,
            prompt=plan.requested_prompt,
            mode=plan.mode,
        )
        updated_plan, updated_trace = await sync_operator_plan_from_trace(
            session,
            workspace_id=plan.workspace_id,
            created_by_id=user.id,
            requested_prompt=plan.requested_prompt,
            trace=trace,
            parent_execution_id=parent_execution.id,
            conversation_id=plan.conversation_id,
            operator_plan_id=plan.id,
            template_slug=plan.template_slug,
            title_override=plan.title,
        )
        await mark_runtime_succeeded(
            session,
            parent_execution,
            response_preview=str((updated_trace.get("trace_summary") or {}).get("summary") or plan.title)[:400],
            details_json=_merge_execution_details(updated_trace),
            artifacts_json=updated_trace.get("artifact_summaries"),
        )
        return success_response(_serialize_operator_plan(updated_plan))
    except Exception as exc:
        await mark_runtime_failed(
            session,
            parent_execution,
            error_message=str(exc),
            details_json=_merge_execution_details(trace or {"mode": plan.mode}),
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
