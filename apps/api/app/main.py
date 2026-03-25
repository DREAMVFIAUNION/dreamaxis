from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.app_config import router as app_config_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.environment import router as environment_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.knowledge_packs import router as knowledge_packs_router
from app.api.v1.messages import router as messages_router
from app.api.v1.models import router as models_router
from app.api.v1.operator_plans import router as operator_plans_router
from app.api.v1.provider_connections import router as provider_connections_router
from app.api.v1.providers import router as providers_router
from app.api.v1.runtime import router as runtime_router
from app.api.v1.skill_packs import router as skill_packs_router
from app.api.v1.skills import router as skills_router
from app.api.v1.workspaces import router as workspaces_router
from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.models.workspace import Workspace
from app.services.demo_data import DEMO_USER_ID, DEMO_WORKSPACE_ID, seed_demo_data
from app.services.knowledge_packs import sync_builtin_knowledge_packs
from app.services.skill_packs import sync_builtin_skill_packs
from sqlalchemy import select

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.knowledge_storage_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    async with SessionLocal() as session:
        await seed_demo_data(session)
        workspace = await session.scalar(select(Workspace).where(Workspace.id == DEMO_WORKSPACE_ID))
        if workspace:
            await sync_builtin_skill_packs(session, workspace)
            await sync_builtin_knowledge_packs(session, workspace, user_id=DEMO_USER_ID)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(app_config_router, prefix=settings.API_V1_PREFIX, tags=["app-config"])
app.include_router(environment_router, prefix=settings.API_V1_PREFIX, tags=["environment"])
app.include_router(provider_connections_router, prefix=f"{settings.API_V1_PREFIX}/provider-connections", tags=["provider-connections"])
app.include_router(providers_router, prefix=f"{settings.API_V1_PREFIX}/providers", tags=["providers"])
app.include_router(models_router, prefix=f"{settings.API_V1_PREFIX}/models", tags=["models"])
app.include_router(workspaces_router, prefix=f"{settings.API_V1_PREFIX}/workspaces", tags=["workspaces"])
app.include_router(conversations_router, prefix=f"{settings.API_V1_PREFIX}/conversations", tags=["conversations"])
app.include_router(messages_router, prefix=f"{settings.API_V1_PREFIX}/messages", tags=["messages"])
app.include_router(operator_plans_router, prefix=settings.API_V1_PREFIX, tags=["operator-plans"])
app.include_router(knowledge_router, prefix=f"{settings.API_V1_PREFIX}/knowledge", tags=["knowledge"])
app.include_router(knowledge_packs_router, prefix=settings.API_V1_PREFIX, tags=["knowledge-packs"])
app.include_router(skill_packs_router, prefix=settings.API_V1_PREFIX, tags=["skill-packs"])
app.include_router(skills_router, prefix=f"{settings.API_V1_PREFIX}/skills", tags=["skills"])
app.include_router(runtime_router, prefix=settings.API_V1_PREFIX, tags=["runtime"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dreamaxis-api"}
