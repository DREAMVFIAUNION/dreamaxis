from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    runtime_execution_id: Mapped[str | None] = mapped_column(ForeignKey("runtime_executions.id"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text())
    sources_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    runtime_execution = relationship("RuntimeExecution", back_populates="messages")
