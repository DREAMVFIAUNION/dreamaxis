from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.conversation import Conversation
from app.models.provider_connection import ProviderConnection
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.conversation import ConversationCreate, ConversationOut, ConversationUpdate

router = APIRouter()


def serialize_conversation(conversation: Conversation) -> dict:
    payload = ConversationOut.model_validate(conversation).model_dump()
    payload["provider_connection_name"] = conversation.provider_connection.name if conversation.provider_connection else None
    return payload


async def ensure_workspace_for_user(session: AsyncSession, *, workspace_id: str, user_id: str) -> Workspace:
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def ensure_provider_connection_for_user(
    session: AsyncSession, *, connection_id: str | None, user_id: str
) -> ProviderConnection | None:
    if not connection_id:
        return None
    connection = await session.scalar(
        select(ProviderConnection).where(ProviderConnection.id == connection_id, ProviderConnection.user_id == user_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    return connection


@router.get("")
async def list_conversations(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    statement = (
        select(Conversation)
        .options(selectinload(Conversation.provider_connection))
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Workspace.owner_id == user.id)
    )
    if workspace_id:
        statement = statement.where(Conversation.workspace_id == workspace_id)
    result = await session.execute(statement.order_by(Conversation.created_at.asc()))
    items = [serialize_conversation(item) for item in result.scalars().all()]
    return paginated_response(items)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    conversation = await session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.provider_connection))
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Conversation.id == conversation_id, Workspace.owner_id == user.id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return success_response(serialize_conversation(conversation))


@router.post("")
async def create_conversation(
    payload: ConversationCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    workspace = await ensure_workspace_for_user(session, workspace_id=payload.workspace_id, user_id=user.id)
    provider_connection = await ensure_provider_connection_for_user(
        session,
        connection_id=payload.provider_connection_id or workspace.default_provider_connection_id,
        user_id=user.id,
    )

    conversation = Conversation(
        id=payload.id or f"conversation-{uuid4().hex[:10]}",
        workspace_id=payload.workspace_id,
        title=payload.title,
        created_by_id=user.id,
        provider_id=payload.provider_id or workspace.default_provider_id,
        model_id=payload.model_id or workspace.default_model_id,
        provider_connection_id=provider_connection.id if provider_connection else None,
        model_name=payload.model_name or workspace.default_model_name,
        use_knowledge=payload.use_knowledge,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    conversation.provider_connection = provider_connection
    return success_response(serialize_conversation(conversation))


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    conversation = await session.scalar(
        select(Conversation)
        .options(selectinload(Conversation.provider_connection))
        .join(Workspace, Conversation.workspace_id == Workspace.id)
        .where(Conversation.id == conversation_id, Workspace.owner_id == user.id)
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if payload.provider_connection_id is not None:
        provider_connection = await ensure_provider_connection_for_user(
            session, connection_id=payload.provider_connection_id, user_id=user.id
        )
        conversation.provider_connection_id = provider_connection.id if provider_connection else None
        conversation.provider_connection = provider_connection
    if payload.title is not None:
        conversation.title = payload.title
    if payload.model_name is not None:
        conversation.model_name = payload.model_name or None
    if payload.use_knowledge is not None:
        conversation.use_knowledge = payload.use_knowledge

    await session.commit()
    await session.refresh(conversation)
    return success_response(serialize_conversation(conversation))
