from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DreamAxis API"
    API_V1_PREFIX: str = "/api/v1"
    AUTH_MODE: str = "local_open"
    DATABASE_URL: str = "postgresql+asyncpg://dreamaxis:dreamaxis@localhost:5432/dreamaxis"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me-dreamaxis-development-secret"
    APP_ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str | None = None
    OPENAI_CHAT_MODEL: str = "gpt-4.1-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536

    KNOWLEDGE_STORAGE_PATH: str = "/tmp/dreamaxis/knowledge"
    KNOWLEDGE_TOP_K: int = 4
    KNOWLEDGE_CHUNK_SIZE: int = 1200
    KNOWLEDGE_CHUNK_OVERLAP: int = 150
    WORKSPACE_ROOT_BASE: str = ""
    RUNTIME_SHARED_TOKEN: str = "dreamaxis-runtime-token"
    RUNTIME_HEARTBEAT_TIMEOUT_SECONDS: int = 45
    RUNTIME_REQUEST_TIMEOUT_SECONDS: int = 30
    ENABLE_BROWSER_RUNTIME: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def knowledge_storage_dir(self) -> Path:
        return Path(self.KNOWLEDGE_STORAGE_PATH)

    @property
    def workspace_root_base_dir(self) -> Path:
        if self.WORKSPACE_ROOT_BASE:
            return Path(self.WORKSPACE_ROOT_BASE).resolve()
        return Path(__file__).resolve().parents[4]


@lru_cache
def get_settings() -> Settings:
    return Settings()
