from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OperatorPlan(TimestampMixin, Base):
    __tablename__ = "operator_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    parent_execution_id: Mapped[str | None] = mapped_column(ForeignKey("runtime_executions.id"), nullable=True, index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(64), default="inspect_desktop")
    status: Mapped[str] = mapped_column(String(64), default="queued")
    operator_stage: Mapped[str] = mapped_column(String(64), default="grounding")
    requested_prompt: Mapped[str] = mapped_column(Text())
    template_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_target_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_target_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pending_approval_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    steps_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    approvals_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    artifacts_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    child_execution_ids_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    trace_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_failure_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
