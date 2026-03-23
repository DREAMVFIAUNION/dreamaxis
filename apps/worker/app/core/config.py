from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DreamAxis Worker"
    API_BASE_URL: str = "http://localhost:8000"
    RUNTIME_SHARED_TOKEN: str = "dreamaxis-runtime-token"
    WORKER_HOST: str = "0.0.0.0"
    WORKER_PORT: int = 8100
    WORKER_RUNTIME_ID: str = "runtime-cli-local"
    WORKER_NAME: str = "Local CLI Runtime"
    WORKER_PUBLIC_URL: str = "http://localhost:8100"
    WORKER_RUNTIME_TYPE: str = "cli"
    WORKER_SCOPE_TYPE: str = "workspace"
    WORKER_SCOPE_REF_ID: str = "workspace-main"
    WORKER_REPO_ROOT: str = ""
    WORKER_SHELL: str = "powershell"
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 15
    CLI_COMMAND_TIMEOUT_SECONDS: int = 30
    CLI_MAX_OUTPUT_CHARS: int = 20000

    @property
    def repo_root_dir(self) -> Path:
        if self.WORKER_REPO_ROOT:
            return Path(self.WORKER_REPO_ROOT).resolve()
        return Path(__file__).resolve().parents[4]


@lru_cache
def get_settings() -> Settings:
    return Settings()
