from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuntimeSessionEvent(TimestampMixin, Base):
    __tablename__ = "runtime_session_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    runtime_session_id: Mapped[str] = mapped_column(ForeignKey("runtime_sessions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    runtime_session = relationship("RuntimeSession", back_populates="events")
