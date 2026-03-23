from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.knowledge import KnowledgeDocumentOut
from app.services.knowledge_service import ingest_upload

router = APIRouter()


@router.get("")
async def list_knowledge_documents(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = None,
    source_type: str | None = None,
    pack_slug: str | None = None,
):
    statement = select(KnowledgeDocument).join(Workspace, KnowledgeDocument.workspace_id == Workspace.id).where(Workspace.owner_id == user.id)
    if workspace_id:
        statement = statement.where(KnowledgeDocument.workspace_id == workspace_id)
    if source_type:
        statement = statement.where(KnowledgeDocument.source_type == source_type)
    if pack_slug:
        statement = statement.where(KnowledgeDocument.knowledge_pack_slug == pack_slug)
    result = await session.execute(statement.order_by(KnowledgeDocument.created_at.desc()))
    items = [KnowledgeDocumentOut.model_validate(item).model_dump() for item in result.scalars().all()]
    return paginated_response(items)


@router.post("/upload")
async def upload_knowledge_document(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
):
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user.id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    document = await ingest_upload(session, workspace, file, user_id=user.id)
    return success_response(KnowledgeDocumentOut.model_validate(document).model_dump())
