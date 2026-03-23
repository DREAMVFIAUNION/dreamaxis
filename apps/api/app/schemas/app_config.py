from __future__ import annotations

from pydantic import BaseModel

from app.schemas.environment import EnvironmentProfile


class AppConfigOut(BaseModel):
    auth_mode: str
    default_workspace_id: str | None = None
    runtime_types: list[str] = []
    feature_flags: dict[str, bool] = {}
    environment_profile: EnvironmentProfile | None = None
