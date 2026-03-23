from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AgentRole(TimestampMixin, Base):
    __tablename__ = "agent_roles"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text())
    allowed_skill_modes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    allowed_runtime_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    default_model_binding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_skill_pack_slugs: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    default_knowledge_pack_slugs: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    skills = relationship("SkillDefinition", back_populates="agent_role")
