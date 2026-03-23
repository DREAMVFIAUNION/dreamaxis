from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.core.security import encrypt_secret
from app.models.provider_connection import ProviderConnection
from app.models.user import User
from app.schemas.provider_connection import (
    ProviderConnectionCreate,
    ProviderConnectionModelOut,
    ProviderConnectionOut,
    ProviderConnectionTestResult,
    ProviderConnectionUpdate,
)
from app.services.assistant_service import generate_entity_id
from app.services.llm_provider import OpenAICompatibleProviderAdapter, ProviderConfigurationError
from app.services.provider_connections import get_connection_secret_meta, merge_connection_models

router = APIRouter()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_provider_connection(connection: ProviderConnection) -> dict:
    payload = ProviderConnectionOut(
        id=connection.id,
        user_id=connection.user_id,
        provider_id=connection.provider_id,
        provider_type=connection.provider_type,
        name=connection.name,
        base_url=connection.base_url,
        model_discovery_mode=connection.model_discovery_mode,
        status=connection.status,
        is_enabled=connection.is_enabled,
        default_model_name=connection.default_model_name,
        default_embedding_model_name=connection.default_embedding_model_name,
        secret=get_connection_secret_meta(connection),
        models=[ProviderConnectionModelOut.model_validate(item) for item in merge_connection_models(connection)],
        last_checked_at=connection.last_checked_at,
        last_error=connection.last_error,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )
    return payload.model_dump()


async def get_connection_or_404(session: AsyncSession, *, connection_id: str, user_id: str) -> ProviderConnection:
    connection = await session.scalar(
        select(ProviderConnection)
        .options(selectinload(ProviderConnection.provider))
        .where(ProviderConnection.id == connection_id, ProviderConnection.user_id == user_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    return connection


def merge_manual_models(connection: ProviderConnection, manual_models: list[dict] | None) -> None:
    discovered = [item for item in (connection.discovered_models_json or []) if item.get("source") == "discovered"]
    connection.discovered_models_json = merge_connection_models(
        connection,
        manual_models=[*discovered, *(manual_models or [])],
    )


@router.get("")
async def list_provider_connections(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    result = await session.execute(
        select(ProviderConnection).where(ProviderConnection.user_id == user.id).order_by(ProviderConnection.created_at.asc())
    )
    items = [serialize_provider_connection(item) for item in result.scalars().all()]
    return paginated_response(items)


@router.post("")
async def create_provider_connection(
    payload: ProviderConnectionCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    connection = ProviderConnection(
        id=generate_entity_id("conn"),
        user_id=user.id,
        provider_type=payload.provider_type,
        name=payload.name,
        base_url=payload.base_url.rstrip("/"),
        api_key_encrypted=encrypt_secret(payload.api_key) if payload.api_key else None,
        model_discovery_mode=payload.model_discovery_mode,
        status="requires_config" if not payload.api_key else "pending",
        default_model_name=payload.default_model_name,
        default_embedding_model_name=payload.default_embedding_model_name,
        discovered_models_json=[item.model_dump() for item in payload.manual_models or []] or None,
    )
    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    return success_response(serialize_provider_connection(connection))


@router.patch("/{connection_id}")
async def update_provider_connection(
    connection_id: str,
    payload: ProviderConnectionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    connection = await get_connection_or_404(session, connection_id=connection_id, user_id=user.id)

    if payload.name is not None:
        connection.name = payload.name
    if payload.base_url is not None:
        connection.base_url = payload.base_url.rstrip("/")
    if payload.api_key is not None:
        connection.api_key_encrypted = encrypt_secret(payload.api_key) if payload.api_key else None
        connection.status = "requires_config" if not payload.api_key else "pending"
    if payload.model_discovery_mode is not None:
        connection.model_discovery_mode = payload.model_discovery_mode
    if payload.status is not None:
        connection.status = payload.status
    if payload.is_enabled is not None:
        connection.is_enabled = payload.is_enabled
    if payload.default_model_name is not None:
        connection.default_model_name = payload.default_model_name or None
    if payload.default_embedding_model_name is not None:
        connection.default_embedding_model_name = payload.default_embedding_model_name or None
    if payload.manual_models is not None:
        merge_manual_models(connection, [item.model_dump() for item in payload.manual_models])

    await session.commit()
    await session.refresh(connection)
    return success_response(serialize_provider_connection(connection))


@router.post("/{connection_id}/test")
async def test_provider_connection(
    connection_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    connection = await get_connection_or_404(session, connection_id=connection_id, user_id=user.id)
    secret = get_connection_secret_meta(connection)
    if not secret["configured"]:
        connection.status = "requires_config"
        connection.last_checked_at = utcnow()
        connection.last_error = "API key is missing."
        await session.commit()
        await session.refresh(connection)
        result = ProviderConnectionTestResult(
            ok=False,
            status=connection.status,
            message=connection.last_error,
            last_checked_at=connection.last_checked_at,
            discovered_model_count=0,
        )
        return success_response(result.model_dump())

    try:
        from app.services.provider_connections import get_connection_api_key

        adapter = OpenAICompatibleProviderAdapter(
            api_key=get_connection_api_key(connection),
            base_url=connection.base_url,
        )
        result = await adapter.test_connection()
        connection.status = result.status
        connection.last_checked_at = utcnow()
        connection.last_error = None if result.ok else result.message
        await session.commit()
        await session.refresh(connection)
        payload = ProviderConnectionTestResult(
            ok=result.ok,
            status=result.status,
            message=result.message,
            last_checked_at=connection.last_checked_at,
            discovered_model_count=result.discovered_model_count,
        )
        return success_response(payload.model_dump())
    except ProviderConfigurationError as exc:
        connection.status = "requires_config"
        connection.last_checked_at = utcnow()
        connection.last_error = str(exc)
        await session.commit()
        await session.refresh(connection)
        payload = ProviderConnectionTestResult(
            ok=False,
            status=connection.status,
            message=str(exc),
            last_checked_at=connection.last_checked_at,
            discovered_model_count=0,
        )
        return success_response(payload.model_dump())
    except Exception as exc:
        connection.status = "error"
        connection.last_checked_at = utcnow()
        connection.last_error = str(exc)
        await session.commit()
        await session.refresh(connection)
        payload = ProviderConnectionTestResult(
            ok=False,
            status=connection.status,
            message=str(exc),
            last_checked_at=connection.last_checked_at,
            discovered_model_count=0,
        )
        return success_response(payload.model_dump())


@router.post("/{connection_id}/sync-models")
async def sync_provider_connection_models(
    connection_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    connection = await get_connection_or_404(session, connection_id=connection_id, user_id=user.id)
    from app.services.provider_connections import get_connection_api_key

    api_key = get_connection_api_key(connection)
    if not api_key:
        raise HTTPException(status_code=400, detail="Provider connection does not have an API key configured")

    try:
        adapter = OpenAICompatibleProviderAdapter(api_key=api_key, base_url=connection.base_url)
        discovered_models = await adapter.list_models()
        manual_models = [item for item in (connection.discovered_models_json or []) if item.get("source") == "manual"]
        connection.discovered_models_json = merge_connection_models(connection, manual_models=[*discovered_models, *manual_models])
        connection.status = "active"
        connection.last_checked_at = utcnow()
        connection.last_error = None
        await session.commit()
        await session.refresh(connection)
        return success_response(
            {
                "connection": serialize_provider_connection(connection),
                "count": len(discovered_models),
            }
        )
    except Exception as exc:
        connection.status = "manual_entry_required"
        connection.last_checked_at = utcnow()
        connection.last_error = str(exc)
        await session.commit()
        await session.refresh(connection)
        return success_response(
            {
                "connection": serialize_provider_connection(connection),
                "count": 0,
                "warning": "Model discovery failed. Add model names manually.",
            }
        )


@router.get("/{connection_id}/models")
async def list_provider_connection_models(
    connection_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    connection = await get_connection_or_404(session, connection_id=connection_id, user_id=user.id)
    models = [ProviderConnectionModelOut.model_validate(item).model_dump() for item in merge_connection_models(connection)]
    return paginated_response(models)
