from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.responses import paginated_response
from app.core.db import SessionLocal
from app.models.provider import Provider
from app.schemas.provider import ProviderOut

router = APIRouter()


@router.get("")
async def list_providers():
    async with SessionLocal() as session:
        result = await session.execute(select(Provider).order_by(Provider.name.asc()))
        providers = [ProviderOut.model_validate(item).model_dump() for item in result.scalars().all()]
        return paginated_response(providers)
