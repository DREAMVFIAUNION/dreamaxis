from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.conversation import ConversationOut
from app.schemas.environment import SkillCompatibilityStatus
from app.schemas.message import MessageOut
from app.schemas.runtime import RuntimeExecutionOut
from app.schemas.common import TimestampedModel


class SkillDefinitionOut(TimestampedModel):
    id: str
    workspace_id: str
    name: str
    slug: str
    description: str
    prompt_template: str
    input_schema: dict[str, Any] | None = None
    tool_capabilities: list[str] | dict[str, Any] | None = None
    knowledge_scope: list[str] | dict[str, Any] | None = None
    required_capabilities: list[str] | None = None
    recommended_capabilities: list[str] | None = None
    workspace_requirements: list[str] | None = None
    enabled: bool
    skill_mode: str
    required_runtime_type: str | None = None
    session_mode: str
    command_template: str | None = None
    working_directory: str | None = None
    agent_role_slug: str | None = None
    pack_slug: str | None = None
    pack_version: str | None = None
    is_builtin: bool
    provider_id: str | None = None
    model_id: str | None = None
    provider_connection_id: str | None = None
    provider_connection_name: str | None = None
    model_name: str | None = None
    allow_model_override: bool
    use_knowledge: bool
    compatibility: SkillCompatibilityStatus | None = None


class SkillUpdate(BaseModel):
    enabled: bool | None = None
    skill_mode: str | None = None
    required_runtime_type: str | None = None
    session_mode: str | None = None
    command_template: str | None = None
    working_directory: str | None = None
    agent_role_slug: str | None = None
    tool_capabilities: list[str] | dict[str, Any] | None = None
    knowledge_scope: list[str] | dict[str, Any] | None = None
    required_capabilities: list[str] | None = None
    recommended_capabilities: list[str] | None = None
    workspace_requirements: list[str] | None = None
    provider_connection_id: str | None = None
    model_name: str | None = None
    allow_model_override: bool | None = None
    use_knowledge: bool | None = None


class SkillRunRequest(BaseModel):
    workspace_id: str
    conversation_id: str | None = None
    variables: dict[str, str] | None = None
    use_knowledge: bool | None = None


class SkillRunResponse(BaseModel):
    conversation: ConversationOut
    execution: RuntimeExecutionOut
    user_message: MessageOut
    assistant_message: MessageOut
