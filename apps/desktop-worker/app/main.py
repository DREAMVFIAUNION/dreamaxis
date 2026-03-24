from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import require_runtime_token
from app.services.desktop_executor import close_session, create_session, execute_actions
from app.services.runtime_client import runtime_registration_context

settings = get_settings()


def success_response(data: Any):
    return {"success": True, "data": data}


class SessionCreatePayload(BaseModel):
    session_id: str
    workspace_id: str
    session_type: str = "desktop"
    reusable: bool = True
    context_json: dict[str, Any]


class ExecutePayload(BaseModel):
    actions: list[dict[str, Any]]


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with runtime_registration_context():
        yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dreamaxis-desktop-worker"}


@app.post("/internal/runtime/sessions")
async def create_runtime_session(
    payload: SessionCreatePayload,
    _: Annotated[str, Depends(require_runtime_token)],
):
    session = create_session(
        session_id=payload.session_id,
        workspace_id=payload.workspace_id,
        session_type=payload.session_type,
        reusable=payload.reusable,
        context_json=payload.context_json,
    )
    return success_response({"session_id": session.session_id, "workspace_id": session.workspace_id, "status": session.status})


@app.post("/internal/runtime/sessions/{session_id}/execute")
async def execute_runtime_actions(
    session_id: str,
    payload: ExecutePayload,
    _: Annotated[str, Depends(require_runtime_token)],
):
    return success_response(execute_actions(session_id, payload.actions))


@app.post("/internal/runtime/sessions/{session_id}/close")
async def close_runtime_session(
    session_id: str,
    _: Annotated[str, Depends(require_runtime_token)],
):
    close_session(session_id)
    return success_response({"session_id": session_id, "status": "closed"})
