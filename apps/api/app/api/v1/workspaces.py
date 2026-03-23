from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut

router = APIRouter()
settings = get_settings()


@router.get("")
async def list_workspaces(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    result = await session.execute(select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.created_at.asc()))
    items = [WorkspaceOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)


@router.post("")
async def create_workspace(
    payload: WorkspaceCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = Workspace(
        id=f"workspace-{uuid4().hex[:10]}",
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        owner_id=user.id,
        workspace_root_path=payload.workspace_root_path or str(settings.workspace_root_base_dir),
        default_provider_id=payload.default_provider_id,
        default_model_id=payload.default_model_id,
        default_provider_connection_id=payload.default_provider_connection_id,
        default_model_name=payload.default_model_name,
        default_embedding_model_name=payload.default_embedding_model_name,
    )
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return success_response(WorkspaceOut.model_validate(workspace).model_dump())
