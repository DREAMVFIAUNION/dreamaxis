from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class RuntimeHostRegisterPayload(BaseModel):
    id: str
    name: str
    runtime_type: str = "cli"
    endpoint_url: str
    capabilities_json: dict[str, Any] | None = None
    scope_type: str = "workspace"
    scope_ref_id: str


class RuntimeHeartbeatPayload(BaseModel):
    capabilities_json: dict[str, Any] | None = None


class RuntimeHostOut(TimestampedModel):
    id: str
    name: str
    runtime_type: str
    endpoint_url: str
    capabilities_json: dict[str, Any] | None = None
    scope_type: str
    scope_ref_id: str
    status: str
    doctor_status: str | None = None
    last_error: str | None = None
    last_heartbeat_at: datetime | None = None
    last_capability_check_at: datetime | None = None


class RuntimeSessionCreate(BaseModel):
    workspace_id: str
    working_directory: str | None = None
    reusable: bool = True


class RuntimeSessionOut(TimestampedModel):
    id: str
    session_type: str
    runtime_id: str
    runtime_name: str | None = None
    workspace_id: str
    created_by_id: str
    status: str
    reusable: bool
    context_json: dict[str, Any] | None = None
    last_activity_at: datetime | None = None


class RuntimeSessionEventOut(TimestampedModel):
    id: str
    runtime_session_id: str
    event_type: str
    message: str | None = None
    payload_json: dict[str, Any] | None = None


class AgentRoleOut(TimestampedModel):
    slug: str
    name: str
    system_prompt: str
    allowed_skill_modes: list[str] | None = None
    allowed_runtime_types: list[str] | None = None
    default_model_binding: dict[str, Any] | None = None
    default_skill_pack_slugs: list[str] | None = None
    default_knowledge_pack_slugs: list[str] | None = None


class CliExecutionResult(BaseModel):
    runtime_id: str
    runtime_session_id: str
    command: str
    cwd: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int
    duration_ms: int | None = None
    artifacts_json: list[dict[str, Any]] | dict[str, Any] | None = None


class BrowserExecutionResult(BaseModel):
    runtime_id: str
    runtime_session_id: str
    actions: list[dict[str, Any]]
    current_url: str | None = None
    title: str | None = None
    extracted_text: str = ""
    duration_ms: int | None = None
    artifacts_json: list[dict[str, Any]] | dict[str, Any] | None = None


class RuntimeExecutionOut(TimestampedModel):
    id: str
    workspace_id: str
    conversation_id: str | None = None
    skill_id: str | None = None
    runtime_id: str | None = None
    runtime_name: str | None = None
    runtime_session_id: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    provider_connection_id: str | None = None
    provider_connection_name: str | None = None
    user_id: str
    source: str
    execution_kind: str
    status: str
    prompt_preview: str | None = None
    command_preview: str | None = None
    response_preview: str | None = None
    error_message: str | None = None
    resolved_model_name: str | None = None
    resolved_base_url: str | None = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int | None = None
    artifacts_json: dict[str, Any] | list[dict[str, Any]] | None = None
    details_json: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
