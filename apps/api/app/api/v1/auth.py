from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.responses import success_response
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.demo_data import DEMO_USER_ID

router = APIRouter()
settings = get_settings()


@router.post("/login")
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_db)]):
    user = await session.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.id)
    return success_response(
        LoginResponse(access_token=token, user=UserOut.model_validate(user)).model_dump()
    )


@router.post("/bootstrap")
async def bootstrap_local_session(session: Annotated[AsyncSession, Depends(get_db)]):
    if settings.AUTH_MODE != "local_open":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Local bootstrap is disabled")

    user = await session.scalar(select(User).where(User.id == DEMO_USER_ID))
    if not user:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Local owner account is not ready")

    token = create_access_token(user.id)
    return success_response(
        LoginResponse(access_token=token, user=UserOut.model_validate(user)).model_dump(),
        message="Local operator session bootstrapped",
    )


@router.get("/me")
async def me(user: Annotated[User, Depends(get_current_user)]):
    return success_response(UserOut.model_validate(user).model_dump())
