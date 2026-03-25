from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
import app.models  # noqa: F401
from app.models.base import Base

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as connection:
        try:
            await connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            pass
        await connection.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
