from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DreamAxis Browser Worker"
    API_BASE_URL: str = "http://localhost:8000"
    RUNTIME_SHARED_TOKEN: str = "dreamaxis-runtime-token"
    BROWSER_WORKER_PUBLIC_URL: str = "http://localhost:8200"
    BROWSER_WORKER_RUNTIME_ID: str = "runtime-browser-local"
    BROWSER_WORKER_NAME: str = "Local Browser Runtime"
    BROWSER_WORKER_SCOPE_TYPE: str = "workspace"
    BROWSER_WORKER_SCOPE_REF_ID: str = "workspace-main"
    BROWSER_WORKER_HEADLESS: bool = True
    BROWSER_WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
