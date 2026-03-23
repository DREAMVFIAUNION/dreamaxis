from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AIModel(TimestampMixin, Base):
    __tablename__ = "llm_models"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32), default="chat")
    context_window: Mapped[int] = mapped_column(Integer, default=8192)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    provider = relationship("Provider", back_populates="models")
    workspaces = relationship("Workspace", back_populates="default_model")
    conversations = relationship("Conversation", back_populates="model")
    runtime_executions = relationship("RuntimeExecution", back_populates="model")
