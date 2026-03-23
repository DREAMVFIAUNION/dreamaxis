from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import success_response
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.environment import EnvironmentOverview
from app.services.environment_doctor import build_doctor_result, build_runtime_snapshots, build_workspace_readiness, environment_profile
from app.services.runtime_registry import list_runtimes_for_workspace

router = APIRouter()


async def list_user_workspaces(session: AsyncSession, user_id: str) -> list[Workspace]:
    result = await session.execute(select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc()))
    return result.scalars().all()


async def get_workspace_or_404(session: AsyncSession, *, workspace_id: str, user_id: str) -> Workspace:
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.get("/environment")
async def get_environment_overview(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspaces = await list_user_workspaces(session, user.id)
    runtimes = []
    for workspace in workspaces:
        runtimes.extend(await list_runtimes_for_workspace(session, workspace.id))
    payload = EnvironmentOverview(
        profile=environment_profile(),
        default_workspace_id=workspaces[0].id if workspaces else None,
        runtime_types=sorted({runtime.runtime_type for runtime in runtimes}),
        runtimes=build_runtime_snapshots(runtimes),
    )
    return success_response(payload.model_dump())


@router.get("/environment/doctor")
async def get_environment_doctor(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    workspaces = await list_user_workspaces(session, user.id)
    if not workspaces:
        raise HTTPException(status_code=404, detail="No workspace available")
    workspace = await get_workspace_or_404(session, workspace_id=workspace_id, user_id=user.id) if workspace_id else workspaces[0]
    runtimes = await list_runtimes_for_workspace(session, workspace.id)
    skills_result = await session.execute(
        select(SkillDefinition).where(SkillDefinition.workspace_id == workspace.id).order_by(SkillDefinition.name.asc())
    )
    payload = build_doctor_result(
        workspace=workspace,
        runtimes=runtimes,
        skills=skills_result.scalars().all(),
        default_workspace_id=workspaces[0].id,
    )
    return success_response(payload)


@router.get("/environment/workspaces/{workspace_id}")
async def get_workspace_environment(
    workspace_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = await get_workspace_or_404(session, workspace_id=workspace_id, user_id=user.id)
    runtimes = await list_runtimes_for_workspace(session, workspace.id)
    payload = build_workspace_readiness(workspace, runtimes)
    return success_response(payload)
