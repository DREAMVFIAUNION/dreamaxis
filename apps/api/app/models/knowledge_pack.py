from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgePack(TimestampMixin, Base):
    __tablename__ = "knowledge_packs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(64), default="1.0.0")
    description: Mapped[str] = mapped_column(Text())
    source_type: Mapped[str] = mapped_column(String(32), default="builtin_pack")
    source_ref: Mapped[str | None] = mapped_column(Text(), nullable=True)
    manifest_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="synced")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
