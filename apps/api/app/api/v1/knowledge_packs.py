from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.knowledge_pack import KnowledgePack
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.knowledge import KnowledgePackOut, KnowledgePackSyncResult
from app.services.knowledge_packs import sync_builtin_knowledge_packs

router = APIRouter()


async def get_workspace_for_user(session: AsyncSession, workspace_id: str, user_id: str) -> Workspace | None:
    return await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))


@router.get("/knowledge-packs")
async def list_knowledge_packs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    statement = select(KnowledgePack).join(Workspace, KnowledgePack.workspace_id == Workspace.id).where(Workspace.owner_id == user.id)
    if workspace_id:
        statement = statement.where(KnowledgePack.workspace_id == workspace_id)
    result = await session.execute(statement.order_by(KnowledgePack.name.asc()))
    items = [KnowledgePackOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)


@router.post("/knowledge-packs/sync")
async def sync_knowledge_packs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str = Query(...),
):
    workspace = await get_workspace_for_user(session, workspace_id, user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    synced_pack_count, synced_document_count = await sync_builtin_knowledge_packs(session, workspace, user_id=user.id)
    payload = KnowledgePackSyncResult(
        synced_pack_count=synced_pack_count,
        synced_document_count=synced_document_count,
    )
    return success_response(payload.model_dump())
