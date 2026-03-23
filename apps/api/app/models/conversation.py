from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    model_id: Mapped[str | None] = mapped_column(ForeignKey("llm_models.id"), nullable=True)
    provider_connection_id: Mapped[str | None] = mapped_column(ForeignKey("provider_connections.id"), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    use_knowledge: Mapped[bool] = mapped_column(Boolean, default=False)

    workspace = relationship("Workspace", back_populates="conversations")
    created_by = relationship("User", back_populates="conversations")
    provider = relationship("Provider", back_populates="conversations")
    model = relationship("AIModel", back_populates="conversations")
    provider_connection = relationship("ProviderConnection", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    runtime_executions = relationship("RuntimeExecution", back_populates="conversation")

    @property
    def provider_connection_name(self) -> str | None:
        provider_connection = self.__dict__.get("provider_connection")
        return provider_connection.name if provider_connection else None
