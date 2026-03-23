from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
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


def _path_style(value: str | None) -> str | None:
    if not value:
        return None
    return "windows" if re.match(r"^[a-zA-Z]:[\\/]", value) else "posix" if value.startswith("/") else None


def _normalize_path(value: str, *, style: str) -> str:
    normalized = value.replace("\\", "/").rstrip("/")
    if style == "windows":
        normalized = normalized.lower()
    return normalized or ("/" if style == "posix" else normalized)


def _path_is_within(candidate: str, root: str, *, style: str) -> bool:
    normalized_candidate = _normalize_path(candidate, style=style)
    normalized_root = _normalize_path(root, style=style)
    if normalized_candidate == normalized_root:
        return True
    prefix = f"{normalized_root}/"
    return normalized_candidate.startswith(prefix)


def runtime_access_mode(runtime: RuntimeHost) -> str | None:
    capabilities = runtime.capabilities_json or {}
    runtime_meta = capabilities.get("runtime") if isinstance(capabilities.get("runtime"), dict) else {}
    access_mode = runtime_meta.get("access_mode") or capabilities.get("access_mode")
    return str(access_mode) if access_mode else None


def runtime_can_access_workspace(runtime: RuntimeHost, workspace_root_path: str | None) -> bool:
    if not workspace_root_path:
        return True

    capabilities = runtime.capabilities_json or {}
    runtime_meta = capabilities.get("runtime") if isinstance(capabilities.get("runtime"), dict) else {}
    runtime_root = runtime_meta.get("repo_root") or capabilities.get("repo_root")
    runtime_style = runtime_meta.get("path_style") or capabilities.get("path_style") or _path_style(str(runtime_root) if runtime_root else None)
    workspace_style = _path_style(workspace_root_path)
    access_mode = runtime_access_mode(runtime)

    if runtime_style and workspace_style and runtime_style != workspace_style:
        return False

    if access_mode == "host":
        return True if not runtime_style or not workspace_style else runtime_style == workspace_style

    if not runtime_root:
        return True

    if not runtime_style or not workspace_style or runtime_style != workspace_style:
        return False

    return _path_is_within(workspace_root_path, str(runtime_root), style=runtime_style)


def runtime_priority(runtime: RuntimeHost, *, workspace_id: str, workspace_root_path: str | None) -> tuple[int, int, int, int, datetime]:
    access_mode = runtime_access_mode(runtime)
    return (
        1 if runtime_can_access_workspace(runtime, workspace_root_path) else 0,
        1 if runtime.scope_type == "workspace" and runtime.scope_ref_id == workspace_id else 0,
        1 if access_mode == "host" else 0,
        1 if runtime.doctor_status == "ready" else 0,
        runtime.last_heartbeat_at or datetime.min.replace(tzinfo=timezone.utc),
    )


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
    result = await session.execute(select(RuntimeHost).order_by(RuntimeHost.created_at.asc()))
    all_runtimes = result.scalars().all()
    runtimes = [
        runtime
        for runtime in all_runtimes
        if runtime.scope_type == "workspace" and runtime.scope_ref_id == workspace_id
    ]
    shared_runtimes = [
        runtime
        for runtime in all_runtimes
        if not (runtime.scope_type == "workspace" and runtime.scope_ref_id == workspace_id)
    ]
    runtimes.extend(shared_runtimes)
    changed = False
    for runtime in runtimes:
        if is_runtime_online(runtime) and runtime_is_stale(runtime):
            runtime.status = "offline"
            changed = True
    if changed:
        await session.commit()
    return runtimes


async def get_online_runtime_for_workspace(
    session: AsyncSession,
    workspace_id: str,
    runtime_type: str = "cli",
    workspace_root_path: str | None = None,
) -> RuntimeHost:
    runtimes = await list_runtimes_for_workspace(session, workspace_id)
    candidates = [runtime for runtime in runtimes if runtime.runtime_type == runtime_type and is_runtime_online(runtime)]
    accessible = [runtime for runtime in candidates if runtime_can_access_workspace(runtime, workspace_root_path)]
    ordered = sorted(
        accessible or candidates,
        key=lambda runtime: runtime_priority(runtime, workspace_id=workspace_id, workspace_root_path=workspace_root_path),
        reverse=True,
    )
    if ordered:
        return ordered[0]
    raise HTTPException(status_code=503, detail=f"No online runtime available for workspace '{workspace_id}' and type '{runtime_type}'")
