from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProviderConnection(TimestampMixin, Base):
    __tablename__ = "provider_connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(50), default="openai_compatible")
    name: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(Text())
    api_key_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    model_discovery_mode: Mapped[str] = mapped_column(String(32), default="auto")
    status: Mapped[str] = mapped_column(String(32), default="requires_config")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_embedding_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_models_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)

    user = relationship("User", back_populates="provider_connections")
    provider = relationship("Provider", back_populates="provider_connections")
    workspaces = relationship("Workspace", back_populates="default_provider_connection")
    conversations = relationship("Conversation", back_populates="provider_connection")
    skills = relationship("SkillDefinition", back_populates="provider_connection")
    runtime_executions = relationship("RuntimeExecution", back_populates="provider_connection")
