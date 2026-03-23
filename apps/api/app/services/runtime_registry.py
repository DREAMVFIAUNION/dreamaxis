from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.runtime_host import RuntimeHost

settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_runtime_online(runtime: RuntimeHost) -> bool:
    return runtime.status in {"online", "online_ready", "online_degraded"}


def runtime_is_stale(runtime: RuntimeHost) -> bool:
    if not runtime.last_heartbeat_at:
        return True
    return runtime.last_heartbeat_at < utcnow() - timedelta(seconds=settings.RUNTIME_HEARTBEAT_TIMEOUT_SECONDS)


def extract_doctor_metadata(capabilities_json: dict[str, Any] | None) -> tuple[str | None, datetime | None]:
    if not capabilities_json:
        return None, None
    environment = capabilities_json.get("environment")
    if not isinstance(environment, dict):
        return None, None
    doctor_status = environment.get("doctor_status")
    checked_at_raw = environment.get("checked_at")
    checked_at: datetime | None = None
    if isinstance(checked_at_raw, str):
        try:
            checked_at = datetime.fromisoformat(checked_at_raw.replace("Z", "+00:00"))
        except ValueError:
            checked_at = None
    return str(doctor_status) if doctor_status else None, checked_at


def resolve_runtime_status(doctor_status: str | None) -> str:
    if doctor_status == "ready":
        return "online_ready"
    if doctor_status in {"degraded", "missing"}:
        return "online_degraded"
    return "online"


async def upsert_runtime_host(
    session: AsyncSession,
    *,
    runtime_id: str,
    name: str,
    runtime_type: str,
    endpoint_url: str,
    capabilities_json: dict | None,
    scope_type: str,
    scope_ref_id: str,
) -> RuntimeHost:
    runtime = await session.scalar(select(RuntimeHost).where(RuntimeHost.id == runtime_id))
    doctor_status, checked_at = extract_doctor_metadata(capabilities_json)
    if not runtime:
        runtime = RuntimeHost(
            id=runtime_id,
            name=name,
            runtime_type=runtime_type,
            endpoint_url=endpoint_url.rstrip("/"),
            capabilities_json=capabilities_json,
            scope_type=scope_type,
            scope_ref_id=scope_ref_id,
            status=resolve_runtime_status(doctor_status),
            doctor_status=doctor_status,
            last_heartbeat_at=utcnow(),
            last_capability_check_at=checked_at,
            last_error=None,
        )
        session.add(runtime)
    else:
        runtime.name = name
        runtime.runtime_type = runtime_type
        runtime.endpoint_url = endpoint_url.rstrip("/")
        runtime.capabilities_json = capabilities_json
        runtime.scope_type = scope_type
        runtime.scope_ref_id = scope_ref_id
        runtime.status = resolve_runtime_status(doctor_status)
        runtime.doctor_status = doctor_status
        runtime.last_heartbeat_at = utcnow()
        runtime.last_capability_check_at = checked_at
        runtime.last_error = None
    await session.commit()
    await session.refresh(runtime)
    return runtime


async def heartbeat_runtime_host(session: AsyncSession, runtime_id: str, capabilities_json: dict[str, Any] | None = None) -> RuntimeHost:
    runtime = await session.scalar(select(RuntimeHost).where(RuntimeHost.id == runtime_id))
    if not runtime:
        raise HTTPException(status_code=404, detail="Runtime not found")
    doctor_status, checked_at = extract_doctor_metadata(capabilities_json)
    if capabilities_json is not None:
        runtime.capabilities_json = capabilities_json
    runtime.status = resolve_runtime_status(doctor_status or runtime.doctor_status)
    runtime.doctor_status = doctor_status or runtime.doctor_status
    runtime.last_heartbeat_at = utcnow()
    runtime.last_capability_check_at = checked_at or runtime.last_capability_check_at
    runtime.last_error = None
    await session.commit()
    await session.refresh(runtime)
    return runtime


async def list_runtimes_for_workspace(session: AsyncSession, workspace_id: str) -> list[RuntimeHost]:
    result = await session.execute(
        select(RuntimeHost)
        .where(RuntimeHost.scope_type == "workspace", RuntimeHost.scope_ref_id == workspace_id)
        .order_by(RuntimeHost.created_at.asc())
    )
    runtimes = result.scalars().all()
    changed = False
    for runtime in runtimes:
        if is_runtime_online(runtime) and runtime_is_stale(runtime):
            runtime.status = "offline"
            changed = True
    if changed:
        await session.commit()
    return runtimes


async def get_online_runtime_for_workspace(session: AsyncSession, workspace_id: str, runtime_type: str = "cli") -> RuntimeHost:
    runtimes = await list_runtimes_for_workspace(session, workspace_id)
    for runtime in runtimes:
        if runtime.runtime_type == runtime_type and is_runtime_online(runtime):
            return runtime
    raise HTTPException(status_code=503, detail=f"No online runtime available for workspace '{workspace_id}' and type '{runtime_type}'")
