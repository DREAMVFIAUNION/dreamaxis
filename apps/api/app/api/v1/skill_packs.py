from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.skill_pack import SkillPack
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.skill_pack import SkillPackImportPayload, SkillPackImportResult, SkillPackOut, SkillPackSyncResult
from app.services.skill_packs import import_skill_pack, sync_builtin_skill_packs

router = APIRouter()


async def get_workspace_for_user(session: AsyncSession, workspace_id: str, user_id: str) -> Workspace | None:
    return await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))


@router.get("/skill-packs")
async def list_skill_packs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    statement = select(SkillPack).join(Workspace, SkillPack.workspace_id == Workspace.id).where(Workspace.owner_id == user.id)
    if workspace_id:
        statement = statement.where(SkillPack.workspace_id == workspace_id)
    result = await session.execute(statement.order_by(SkillPack.name.asc()))
    items = [SkillPackOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)


@router.post("/skill-packs/import")
async def import_workspace_skill_pack(
    payload: SkillPackImportPayload,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = await get_workspace_for_user(session, payload.workspace_id, user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    pack, imported_skill_count = await import_skill_pack(session, workspace, payload.source_path)
    response = SkillPackImportResult(pack=SkillPackOut.model_validate(pack), imported_skill_count=imported_skill_count)
    return success_response(response.model_dump())


@router.post("/skill-packs/sync")
async def sync_workspace_skill_packs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str = Query(...),
):
    workspace = await get_workspace_for_user(session, workspace_id, user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    synced_pack_count, synced_skill_count = await sync_builtin_skill_packs(session, workspace)
    response = SkillPackSyncResult(synced_pack_count=synced_pack_count, synced_skill_count=synced_skill_count)
    return success_response(response.model_dump())
