from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.core.security import require_runtime_token
from app.services.browser_executor import close_session, create_session, execute_actions, shutdown_browser, startup_browser
from app.services.runtime_client import runtime_registration_context


def success_response(data: Any):
    return {"success": True, "data": data}


class SessionCreatePayload(BaseModel):
    session_id: str
    workspace_id: str
    session_type: str = "browser"
    reusable: bool = True
    context_json: dict[str, Any]


class ExecutePayload(BaseModel):
    actions: list[dict[str, Any]]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await startup_browser()
    async with runtime_registration_context():
        yield
    await shutdown_browser()


app = FastAPI(title="DreamAxis Browser Worker", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dreamaxis-browser-worker"}


@app.post("/internal/runtime/sessions")
async def create_runtime_session(
    payload: SessionCreatePayload,
    _: Annotated[str, Depends(require_runtime_token)],
):
    session = await create_session(
        session_id=payload.session_id,
        workspace_id=payload.workspace_id,
        session_type=payload.session_type,
        reusable=payload.reusable,
        context_json=payload.context_json,
    )
    return success_response(
        {
            "session_id": session.session_id,
            "workspace_id": session.workspace_id,
            "status": session.status,
        }
    )


@app.post("/internal/runtime/sessions/{session_id}/execute")
async def execute_runtime_actions(
    session_id: str,
    payload: ExecutePayload,
    _: Annotated[str, Depends(require_runtime_token)],
):
    return success_response(await execute_actions(session_id, payload.actions))


@app.post("/internal/runtime/sessions/{session_id}/close")
async def close_runtime_session(
    session_id: str,
    _: Annotated[str, Depends(require_runtime_token)],
):
    await close_session(session_id)
    return success_response({"session_id": session_id, "status": "closed"})
