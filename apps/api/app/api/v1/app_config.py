from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.responses import success_response
from app.schemas.app_config import AppConfigOut
from app.services.environment_doctor import environment_profile
from app.services.demo_data import DEMO_WORKSPACE_ID

router = APIRouter()
settings = get_settings()


@router.get("/app-config")
async def get_app_config():
    runtime_types = ["cli"]
    if settings.ENABLE_BROWSER_RUNTIME:
        runtime_types.append("browser")

    payload = AppConfigOut(
        auth_mode=settings.AUTH_MODE,
        default_workspace_id=DEMO_WORKSPACE_ID,
        runtime_types=runtime_types,
        feature_flags={
            "browser_runtime": settings.ENABLE_BROWSER_RUNTIME,
            "knowledge_packs": True,
            "skill_packs": True,
            "environment_doctor": True,
        },
        environment_profile=environment_profile(),
    )
    return success_response(payload.model_dump())
