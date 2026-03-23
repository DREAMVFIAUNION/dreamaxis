from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Provider(TimestampMixin, Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="active")

    models = relationship("AIModel", back_populates="provider")
    workspaces = relationship("Workspace", back_populates="default_provider")
    provider_connections = relationship("ProviderConnection", back_populates="provider")
    conversations = relationship("Conversation", back_populates="provider")
    runtime_executions = relationship("RuntimeExecution", back_populates="provider")
