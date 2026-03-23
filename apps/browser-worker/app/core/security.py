from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.config import get_settings

settings = get_settings()


def require_runtime_token(x_runtime_token: Annotated[str | None, Header()] = None) -> str:
    if not x_runtime_token or x_runtime_token != settings.RUNTIME_SHARED_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid runtime token")
    return x_runtime_token
