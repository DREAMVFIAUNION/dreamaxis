from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuntimeHost(TimestampMixin, Base):
    __tablename__ = "runtimes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    runtime_type: Mapped[str] = mapped_column(String(32), default="cli")
    endpoint_url: Mapped[str] = mapped_column(Text())
    capabilities_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="workspace")
    scope_ref_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="online")
    doctor_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_capability_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions = relationship("RuntimeSession", back_populates="runtime", cascade="all, delete-orphan")
    executions = relationship("RuntimeExecution", back_populates="runtime")
