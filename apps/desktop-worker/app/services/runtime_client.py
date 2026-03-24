from __future__ import annotations

import asyncio
import contextlib
import platform
import shutil

import httpx

from app.core.config import get_settings

settings = get_settings()


def probe_environment() -> dict:
    current_platform = platform.system()
    is_windows = current_platform == "Windows"
    repo_root = settings.DESKTOP_WORKER_REPO_ROOT
    path_style = "windows" if repo_root and current_platform == "Windows" else ("posix" if repo_root else None)
    return {
        "os": {
            "platform": current_platform,
            "release": platform.release(),
            "version": platform.version(),
        },
        "supports_list_windows": is_windows,
        "supports_focus_window": is_windows,
        "supports_launch_app": is_windows,
        "supports_capture_screen": is_windows,
        "supports_extract_text": is_windows and bool(shutil.which("tesseract")),
        "supports_accessibility_tree": False,
        "supports_click": is_windows,
        "supports_type_text": is_windows,
        "supports_press_hotkey": is_windows,
        "runtime": {
            "desktop_alpha": True,
            "windows_only": True,
            "gated_actions": True,
            "proposal_only_writes": True,
            "access_mode": settings.DESKTOP_WORKER_ACCESS_MODE,
            "host_platform": current_platform,
            "native_windows_host": is_windows,
            "repo_root": repo_root,
            "path_style": path_style,
            "degraded_reason": None if is_windows else "Desktop worker is not running on a native Windows host.",
        },
    }


def _headers() -> dict[str, str]:
    return {"X-Runtime-Token": settings.RUNTIME_SHARED_TOKEN}


def registration_payload() -> dict:
    environment = probe_environment()
    return {
        "id": settings.DESKTOP_WORKER_RUNTIME_ID,
        "name": settings.DESKTOP_WORKER_NAME,
        "runtime_type": "desktop",
        "endpoint_url": settings.DESKTOP_WORKER_PUBLIC_URL.rstrip("/"),
        "capabilities_json": {
            **environment,
            "environment": environment,
        },
        "scope_type": settings.DESKTOP_WORKER_SCOPE_TYPE,
        "scope_ref_id": settings.DESKTOP_WORKER_SCOPE_REF_ID,
    }


async def register_runtime() -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.API_BASE_URL.rstrip('/')}/api/v1/runtimes/register",
            json=registration_payload(),
            headers=_headers(),
        )
        response.raise_for_status()


async def wait_for_registration(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            await register_runtime()
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(delay_seconds)
    if last_error:
        raise last_error


async def heartbeat() -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.API_BASE_URL.rstrip('/')}/api/v1/runtimes/{settings.DESKTOP_WORKER_RUNTIME_ID}/heartbeat",
            json={"capabilities_json": registration_payload()["capabilities_json"]},
            headers=_headers(),
        )
        response.raise_for_status()


async def heartbeat_loop() -> None:
    while True:
        try:
            await heartbeat()
        except Exception:
            pass
        await asyncio.sleep(settings.DESKTOP_WORKER_HEARTBEAT_INTERVAL_SECONDS)


@contextlib.asynccontextmanager
async def runtime_registration_context():
    await wait_for_registration()
    task = asyncio.create_task(heartbeat_loop(), name="dreamaxis-desktop-worker-heartbeat")
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
