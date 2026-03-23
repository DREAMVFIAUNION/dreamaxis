from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    workspace_root_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    default_provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    default_model_id: Mapped[str | None] = mapped_column(ForeignKey("llm_models.id"), nullable=True)
    default_provider_connection_id: Mapped[str | None] = mapped_column(ForeignKey("provider_connections.id"), nullable=True)
    default_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_embedding_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    owner = relationship("User", back_populates="workspaces")
    default_provider = relationship("Provider", back_populates="workspaces")
    default_model = relationship("AIModel", back_populates="workspaces")
    default_provider_connection = relationship("ProviderConnection", back_populates="workspaces")
    conversations = relationship("Conversation", back_populates="workspace")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="workspace", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="workspace", cascade="all, delete-orphan")
    skills = relationship("SkillDefinition", back_populates="workspace", cascade="all, delete-orphan")
    runtime_executions = relationship("RuntimeExecution", back_populates="workspace", cascade="all, delete-orphan")
    runtime_sessions = relationship("RuntimeSession", back_populates="workspace", cascade="all, delete-orphan")
