from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decrypt_secret, mask_secret
from app.models.provider_connection import ProviderConnection

settings = get_settings()


@dataclass
class ResolvedProviderConnection:
    provider_connection_id: str | None
    provider_connection_name: str
    provider_id: str | None
    provider_type: str
    base_url: str | None
    api_key: str
    default_model_name: str | None = None
    default_embedding_model_name: str | None = None
    is_fallback: bool = False


def get_connection_api_key(connection: ProviderConnection) -> str | None:
    if not connection.api_key_encrypted:
        return None
    return decrypt_secret(connection.api_key_encrypted)


def get_connection_secret_meta(connection: ProviderConnection) -> dict:
    api_key = get_connection_api_key(connection)
    return {"masked_value": mask_secret(api_key), "configured": bool(api_key)}


def merge_connection_models(
    connection: ProviderConnection,
    manual_models: list[dict] | None = None,
) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def push(entry: dict) -> None:
        name = str(entry.get("name") or "").strip()
        kind = str(entry.get("kind") or "chat").strip() or "chat"
        if not name:
            return
        key = (name, kind)
        if key in seen:
            return
        seen.add(key)
        merged.append(
            {
                "name": name,
                "kind": kind,
                "source": str(entry.get("source") or "manual"),
                "metadata": entry.get("metadata") if isinstance(entry.get("metadata"), dict) else None,
            }
        )

    for item in connection.discovered_models_json or []:
        if isinstance(item, dict):
            push(item)
    for item in manual_models or []:
        if isinstance(item, dict):
            push(item)
    if connection.default_model_name:
        push({"name": connection.default_model_name, "kind": "chat", "source": "manual"})
    if connection.default_embedding_model_name:
        push({"name": connection.default_embedding_model_name, "kind": "embedding", "source": "manual"})
    return merged


async def get_provider_connection_for_user(
    session: AsyncSession,
    *,
    user_id: str,
    connection_id: str | None,
) -> ProviderConnection | None:
    if not connection_id:
        return None
    return await session.scalar(
        select(ProviderConnection).where(ProviderConnection.id == connection_id, ProviderConnection.user_id == user_id)
    )


async def get_first_enabled_provider_connection(session: AsyncSession, *, user_id: str) -> ProviderConnection | None:
    return await session.scalar(
        select(ProviderConnection)
        .where(ProviderConnection.user_id == user_id, ProviderConnection.is_enabled.is_(True))
        .order_by(ProviderConnection.created_at.asc())
    )


async def resolve_provider_connection_or_fallback(
    session: AsyncSession,
    *,
    user_id: str,
    connection_id: str | None,
) -> ResolvedProviderConnection | None:
    connection = await get_provider_connection_for_user(session, user_id=user_id, connection_id=connection_id)
    if connection is None and connection_id is None:
        connection = await get_first_enabled_provider_connection(session, user_id=user_id)

    if connection is not None:
        api_key = get_connection_api_key(connection)
        if api_key:
            return ResolvedProviderConnection(
                provider_connection_id=connection.id,
                provider_connection_name=connection.name,
                provider_id=connection.provider_id,
                provider_type=connection.provider_type,
                base_url=connection.base_url,
                api_key=api_key,
                default_model_name=connection.default_model_name,
                default_embedding_model_name=connection.default_embedding_model_name,
            )

    if settings.OPENAI_API_KEY:
        return ResolvedProviderConnection(
            provider_connection_id=None,
            provider_connection_name="Environment Fallback",
            provider_id=None,
            provider_type="openai_compatible",
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            default_model_name=settings.OPENAI_CHAT_MODEL,
            default_embedding_model_name=settings.OPENAI_EMBEDDING_MODEL,
            is_fallback=True,
        )
    return None
