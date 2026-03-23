from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.responses import paginated_response
from app.models.ai_model import AIModel
from app.schemas.ai_model import AIModelOut

router = APIRouter()


@router.get("")
async def list_models(kind: str | None = Query(default=None)):
    async with SessionLocal() as session:
        statement = select(AIModel)
        if kind:
            statement = statement.where(AIModel.kind == kind)
        result = await session.execute(statement.order_by(AIModel.kind.asc(), AIModel.is_default.desc(), AIModel.name.asc()))
        models = [AIModelOut.model_validate(item).model_dump() for item in result.scalars().all()]
        return paginated_response(models)
