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
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.operator_plan import OperatorPlanActionReview, OperatorPlanCreate, OperatorPlanOut
from app.services.operator_plans import (
    get_operator_plan_or_404,
    list_builtin_operator_templates,
    resolve_operator_plan_input,
)
from app.services.operator_plan_executor import create_and_execute_operator_plan, resume_operator_plan_execution, review_operator_plan

router = APIRouter()


def _serialize_operator_plan(plan) -> dict[str, Any]:
    return OperatorPlanOut.model_validate(plan).model_dump()
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
    try:
        plan = await create_and_execute_operator_plan(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            title=resolved_input["title"] or "",
            prompt=resolved_input["prompt"] or "",
            mode=resolved_input["mode"],
            template_slug=resolved_input["template_slug"],
        )
        return success_response(_serialize_operator_plan(plan))
    except Exception as exc:
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
    workspace = await _get_workspace_or_404(session, workspace_id=plan.workspace_id, user_id=user.id)
    conversation = await _get_conversation_or_404(session, conversation_id=plan.conversation_id, workspace_id=workspace.id, user_id=user.id)
    try:
        updated_plan = await review_operator_plan(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            plan=plan,
            decision="approved",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    workspace = await _get_workspace_or_404(session, workspace_id=plan.workspace_id, user_id=user.id)
    conversation = await _get_conversation_or_404(session, conversation_id=plan.conversation_id, workspace_id=workspace.id, user_id=user.id)
    try:
        updated_plan = await review_operator_plan(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            plan=plan,
            decision="denied",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    try:
        updated_plan = await resume_operator_plan_execution(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            plan=plan,
        )
        return success_response(_serialize_operator_plan(updated_plan))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
