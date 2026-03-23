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
    environment = probe_environment()
    return {
        "id": settings.WORKER_RUNTIME_ID,
        "name": settings.WORKER_NAME,
        "runtime_type": settings.WORKER_RUNTIME_TYPE,
        "endpoint_url": settings.WORKER_PUBLIC_URL.rstrip("/"),
        "capabilities_json": {
            "shell": settings.WORKER_SHELL,
            "supports_exec_command": True,
            "supports_read_file": True,
            "supports_list_dir": True,
            "supports_write_file": False,
            "runtime": {
                "shell": settings.WORKER_SHELL,
                "supports_exec_command": True,
                "supports_read_file": True,
                "supports_list_dir": True,
                "supports_write_file": False,
            },
            "environment": environment,
        },
        "scope_type": settings.WORKER_SCOPE_TYPE,
        "scope_ref_id": settings.WORKER_SCOPE_REF_ID,
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
            f"{settings.API_BASE_URL.rstrip('/')}/api/v1/runtimes/{settings.WORKER_RUNTIME_ID}/heartbeat",
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
        await asyncio.sleep(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS)


@contextlib.asynccontextmanager
async def runtime_registration_context():
    await wait_for_registration()
    task = asyncio.create_task(heartbeat_loop(), name="dreamaxis-worker-heartbeat")
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
