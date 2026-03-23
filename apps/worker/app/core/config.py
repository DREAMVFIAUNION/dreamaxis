from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

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
    WORKER_ACCESS_MODE: str = "auto"
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 15
    CLI_COMMAND_TIMEOUT_SECONDS: int = 30
    CLI_MAX_OUTPUT_CHARS: int = 20000

    @property
    def repo_root_dir(self) -> Path:
        if self.WORKER_REPO_ROOT:
            return Path(self.WORKER_REPO_ROOT).resolve()
        return Path(__file__).resolve().parents[4]

    @property
    def worker_path_style(self) -> str:
        repo_root = str(self.repo_root_dir)
        return "windows" if re.match(r"^[a-zA-Z]:[\\/]", repo_root) else "posix"

    @property
    def worker_access_mode(self) -> str:
        if self.WORKER_ACCESS_MODE and self.WORKER_ACCESS_MODE != "auto":
            return self.WORKER_ACCESS_MODE
        return "host" if self.worker_path_style == "windows" else "mounted"


@lru_cache
def get_settings() -> Settings:
    return Settings()
