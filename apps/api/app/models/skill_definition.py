from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SkillDefinition(TimestampMixin, Base):
    __tablename__ = "skill_definitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text())
    prompt_template: Mapped[str] = mapped_column(Text())
    input_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_capabilities: Mapped[list[str] | dict | None] = mapped_column(JSON, nullable=True)
    knowledge_scope: Mapped[list[str] | dict | None] = mapped_column(JSON, nullable=True)
    required_capabilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recommended_capabilities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    workspace_requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_mode: Mapped[str] = mapped_column(String(32), default="prompt")
    required_runtime_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    session_mode: Mapped[str] = mapped_column(String(32), default="reuse")
    command_template: Mapped[str | None] = mapped_column(Text(), nullable=True)
    working_directory: Mapped[str | None] = mapped_column(String(512), nullable=True)
    agent_role_slug: Mapped[str | None] = mapped_column(ForeignKey("agent_roles.slug"), nullable=True)
    pack_slug: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    pack_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"), nullable=True)
    model_id: Mapped[str | None] = mapped_column(ForeignKey("llm_models.id"), nullable=True)
    provider_connection_id: Mapped[str | None] = mapped_column(ForeignKey("provider_connections.id"), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    allow_model_override: Mapped[bool] = mapped_column(Boolean, default=True)
    use_knowledge: Mapped[bool] = mapped_column(Boolean, default=True)

    workspace = relationship("Workspace", back_populates="skills")
    agent_role = relationship("AgentRole", back_populates="skills")
    provider = relationship("Provider")
    model = relationship("AIModel")
    provider_connection = relationship("ProviderConnection", back_populates="skills")
    runtime_executions = relationship("RuntimeExecution", back_populates="skill")

    @property
    def provider_connection_name(self) -> str | None:
        provider_connection = self.__dict__.get("provider_connection")
        return provider_connection.name if provider_connection else None
