from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DreamAxis Desktop Worker"
    API_BASE_URL: str = "http://localhost:8000"
    RUNTIME_SHARED_TOKEN: str = "dreamaxis-runtime-token"
    DESKTOP_WORKER_PUBLIC_URL: str = "http://localhost:8300"
    DESKTOP_WORKER_RUNTIME_ID: str = "runtime-desktop-local"
    DESKTOP_WORKER_NAME: str = "Local Desktop Runtime"
    DESKTOP_WORKER_SCOPE_TYPE: str = "workspace"
    DESKTOP_WORKER_SCOPE_REF_ID: str = "workspace-main"
    DESKTOP_WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 15
    DESKTOP_WORKER_ACCESS_MODE: str = "container"
    DESKTOP_WORKER_REPO_ROOT: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
