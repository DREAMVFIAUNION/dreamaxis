from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimestampedModel
from app.schemas.message import ChatMode


class OperatorPlanTemplateOut(BaseModel):
    slug: str
    title: str
    description: str
    mode: ChatMode
    prompt: str
    tags: list[str]


class OperatorPlanCreate(BaseModel):
    workspace_id: str
    conversation_id: str | None = None
    prompt: str | None = None
    mode: ChatMode | None = None
    template_slug: str | None = None
    title: str | None = None


class OperatorPlanActionReview(BaseModel):
    decision: str


class OperatorPlanOut(TimestampedModel):
    id: str
    workspace_id: str
    conversation_id: str | None = None
    parent_execution_id: str | None = None
    created_by_id: str
    title: str
    mode: str
    status: str
    operator_stage: str
    requested_prompt: str
    template_slug: str | None = None
    primary_target_label: str | None = None
    primary_target_value: str | None = None
    pending_approval_count: int
    summary_json: dict[str, Any] | None = None
    steps_json: list[dict[str, Any]] | None = None
    approvals_json: list[dict[str, Any]] | None = None
    artifacts_json: list[dict[str, Any]] | None = None
    child_execution_ids_json: list[str] | None = None
    trace_json: dict[str, Any] | None = None
    last_failure_summary: str | None = None


class OperatorPlanListResponse(BaseModel):
    items: list[OperatorPlanOut]
    templates: list[OperatorPlanTemplateOut]
