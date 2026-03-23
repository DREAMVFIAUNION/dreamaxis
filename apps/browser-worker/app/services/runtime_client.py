from __future__ import annotations

import asyncio
import contextlib

import httpx

from app.core.config import get_settings
from app.services.environment_probe import probe_environment

settings = get_settings()


def _headers() -> dict[str, str]:
    return {"X-Runtime-Token": settings.RUNTIME_SHARED_TOKEN}


def registration_payload() -> dict:
    environment = probe_environment(browser_ready=True)
    return {
        "id": settings.BROWSER_WORKER_RUNTIME_ID,
        "name": settings.BROWSER_WORKER_NAME,
        "runtime_type": "browser",
        "endpoint_url": settings.BROWSER_WORKER_PUBLIC_URL.rstrip("/"),
        "capabilities_json": {
            "supports_open_url": True,
            "supports_click": True,
            "supports_hover": True,
            "supports_type": True,
            "supports_select_option": True,
            "supports_press": True,
            "supports_wait_for": True,
            "supports_extract_text": True,
            "supports_extract_links": True,
            "supports_take_screenshot": True,
            "supports_list_tabs": True,
            "supports_close_tab": True,
            "headless": settings.BROWSER_WORKER_HEADLESS,
            "runtime": {
                "supports_open_url": True,
                "supports_click": True,
                "supports_hover": True,
                "supports_type": True,
                "supports_select_option": True,
                "supports_press": True,
                "supports_wait_for": True,
                "supports_extract_text": True,
                "supports_extract_links": True,
                "supports_take_screenshot": True,
                "supports_list_tabs": True,
                "supports_close_tab": True,
                "headless": settings.BROWSER_WORKER_HEADLESS,
            },
            "environment": environment,
        },
        "scope_type": settings.BROWSER_WORKER_SCOPE_TYPE,
        "scope_ref_id": settings.BROWSER_WORKER_SCOPE_REF_ID,
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
            f"{settings.API_BASE_URL.rstrip('/')}/api/v1/runtimes/{settings.BROWSER_WORKER_RUNTIME_ID}/heartbeat",
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
        await asyncio.sleep(settings.BROWSER_WORKER_HEARTBEAT_INTERVAL_SECONDS)


@contextlib.asynccontextmanager
async def runtime_registration_context():
    await wait_for_registration()
    task = asyncio.create_task(heartbeat_loop(), name="dreamaxis-browser-worker-heartbeat")
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
