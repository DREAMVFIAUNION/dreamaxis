from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RuntimeSession(TimestampMixin, Base):
    __tablename__ = "runtime_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_type: Mapped[str] = mapped_column(String(32), default="cli")
    runtime_id: Mapped[str] = mapped_column(ForeignKey("runtimes.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="idle")
    reusable: Mapped[bool] = mapped_column(Boolean, default=True)
    context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runtime = relationship("RuntimeHost", back_populates="sessions")
    workspace = relationship("Workspace", back_populates="runtime_sessions")
    created_by = relationship("User")
    events = relationship("RuntimeSessionEvent", back_populates="runtime_session", cascade="all, delete-orphan")
    executions = relationship("RuntimeExecution", back_populates="runtime_session")

    @property
    def cwd(self) -> str | None:
        return (self.context_json or {}).get("cwd")

    @property
    def repo_root(self) -> str | None:
        return (self.context_json or {}).get("repo_root")

    @property
    def runtime_name(self) -> str | None:
        runtime = self.__dict__.get("runtime")
        return runtime.name if runtime else None
