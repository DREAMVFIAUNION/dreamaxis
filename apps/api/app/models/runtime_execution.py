from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuntimeExecution(TimestampMixin, Base):
    __tablename__ = "runtime_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skill_definitions.id"), nullable=True, index=True)
    runtime_id: Mapped[str | None] = mapped_column(ForeignKey("runtimes.id"), nullable=True, index=True)
    runtime_session_id: Mapped[str | None] = mapped_column(ForeignKey("runtime_sessions.id"), nullable=True, index=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    model_id: Mapped[str | None] = mapped_column(ForeignKey("llm_models.id"), nullable=True)
    provider_connection_id: Mapped[str | None] = mapped_column(ForeignKey("provider_connections.id"), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source: Mapped[str] = mapped_column(String(32), default="chat")
    execution_kind: Mapped[str] = mapped_column(String(32), default="chat")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    prompt_preview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    command_preview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    response_preview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolved_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_base_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifacts_json: Mapped[list[dict] | dict | None] = mapped_column(JSON, nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace", back_populates="runtime_executions")
    conversation = relationship("Conversation", back_populates="runtime_executions")
    skill = relationship("SkillDefinition", back_populates="runtime_executions")
    runtime = relationship("RuntimeHost", back_populates="executions")
    runtime_session = relationship("RuntimeSession", back_populates="executions")
    provider = relationship("Provider", back_populates="runtime_executions")
    model = relationship("AIModel", back_populates="runtime_executions")
    provider_connection = relationship("ProviderConnection", back_populates="runtime_executions")
    user = relationship("User")
    messages = relationship("Message", back_populates="runtime_execution")

    @property
    def provider_connection_name(self) -> str | None:
        provider_connection = self.__dict__.get("provider_connection")
        return provider_connection.name if provider_connection else None

    @property
    def runtime_name(self) -> str | None:
        runtime = self.__dict__.get("runtime")
        return runtime.name if runtime else None
