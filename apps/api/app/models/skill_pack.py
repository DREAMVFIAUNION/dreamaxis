from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SkillPack(TimestampMixin, Base):
    __tablename__ = "skill_packs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(64), default="1.0.0")
    description: Mapped[str] = mapped_column(Text())
    source_type: Mapped[str] = mapped_column(String(32), default="builtin")
    source_ref: Mapped[str | None] = mapped_column(Text(), nullable=True)
    manifest_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="synced")
    tool_capabilities_json: Mapped[list[str] | dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
