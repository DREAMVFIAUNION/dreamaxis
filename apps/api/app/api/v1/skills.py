from __future__ import annotations

from collections import defaultdict
import json
from string import Formatter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.responses import paginated_response, success_response
from app.models.agent_role import AgentRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.provider_connection import ProviderConnection
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.conversation import ConversationOut
from app.schemas.environment import SkillCompatibilityStatus
from app.schemas.message import MessageOut
from app.schemas.runtime import RuntimeExecutionOut
from app.schemas.skill import SkillDefinitionOut, SkillRunRequest, SkillRunResponse, SkillUpdate
from app.services.assistant_service import generate_entity_id, generate_message_id
from app.services.chat_service import build_llm_messages, resolve_conversation_context, serialize_sources, summarize_details
from app.services.environment_doctor import build_machine_capabilities, build_workspace_readiness, evaluate_skill_compatibility
from app.services.knowledge_service import retrieve_relevant_chunks
from app.services.llm_provider import OpenAICompatibleProviderAdapter
from app.services.runtime_dispatcher import dispatch_browser_execution, dispatch_cli_execution, render_template
from app.services.runtime_registry import list_runtimes_for_workspace
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded

router = APIRouter()


READ_ONLY_CLI_TOKENS = ["get-childitem", "get-content", "select-string", "git diff", "npm run lint", "npm run build", "npm run test"]
INTERACTIVE_BROWSER_ACTIONS = {"click", "type", "select_option", "press"}


def infer_skill_scenario_tags(skill: SkillDefinition) -> list[str]:
    slug = skill.slug.lower()
    name = skill.name.lower()
    description = skill.description.lower()
    tags: list[str] = []
    if any(token in slug or token in name or token in description for token in ["repo", "manifest", "readme", "architecture"]):
        tags.append("repo_onboarding")
    if any(token in slug or token in name or token in description for token in ["trace", "diff", "handler", "route", "inventory"]):
        tags.append("trace_feature_or_bug")
    if any(token in slug or token in name or token in description for token in ["lint", "build", "test", "capture", "verify", "screenshot"]):
        tags.append("run_verification_workflow")
    if any(token in slug or token in name or token in description for token in ["knowledge", "research", "incident", "summary"]):
        tags.append("knowledge_assisted_troubleshooting")
    if not tags and skill.skill_mode == "prompt":
        tags.append("repo_onboarding")
    return list(dict.fromkeys(tags))


def infer_skill_read_only(skill: SkillDefinition) -> bool:
    if skill.skill_mode == "prompt":
        return True
    if skill.skill_mode == "cli":
        command = (skill.command_template or "").lower()
        return any(token in command for token in READ_ONLY_CLI_TOKENS)
    if skill.skill_mode == "browser":
        capabilities = skill.tool_capabilities if isinstance(skill.tool_capabilities, list) else []
        return not any(capability in INTERACTIVE_BROWSER_ACTIONS for capability in capabilities)
    return True


def infer_skill_safety_level(skill: SkillDefinition) -> str:
    if skill.skill_mode == "prompt":
        return "advisory"
    return "read_only" if infer_skill_read_only(skill) else "guarded"


def infer_chat_modes(skill: SkillDefinition) -> list[str]:
    scenario_tags = infer_skill_scenario_tags(skill)
    modes: list[str] = []
    if "repo_onboarding" in scenario_tags:
        modes.append("understand")
    if "trace_feature_or_bug" in scenario_tags:
        modes.append("inspect")
    if "verify_local_readiness" in scenario_tags or "run_verification_workflow" in scenario_tags:
        modes.append("verify")
    if "knowledge_assisted_troubleshooting" in scenario_tags:
        modes.append("propose_fix")
    if skill.skill_mode == "prompt":
        modes.extend(["understand", "inspect"])
    if infer_skill_read_only(skill):
        modes.append("verify")
    return list(dict.fromkeys(modes))


def infer_supports_proposal_output(skill: SkillDefinition) -> bool:
    scenario_tags = infer_skill_scenario_tags(skill)
    return skill.skill_mode == "prompt" or "knowledge_assisted_troubleshooting" in scenario_tags


def infer_chat_callable(skill: SkillDefinition, compatibility: dict | None = None) -> bool:
    if not skill.enabled:
        return False
    if compatibility and compatibility.get("status") == "blocked":
        return False
    return skill.skill_mode in {"prompt", "cli", "browser"}


def serialize_skill(
    skill: SkillDefinition,
    *,
    compatibility: dict | None = None,
) -> dict:
    payload = SkillDefinitionOut.model_validate(skill).model_dump()
    payload["provider_connection_name"] = skill.provider_connection.name if skill.provider_connection else None
    payload["chat_callable"] = infer_chat_callable(skill, compatibility)
    payload["chat_modes"] = infer_chat_modes(skill)
    payload["safety_level"] = infer_skill_safety_level(skill)
    payload["scenario_tags"] = infer_skill_scenario_tags(skill)
    payload["is_read_only"] = infer_skill_read_only(skill)
    payload["supports_proposal_output"] = infer_supports_proposal_output(skill)
    payload["compatibility"] = compatibility
    return payload


async def ensure_provider_connection_for_user(
    session: AsyncSession, *, connection_id: str | None, user_id: str
) -> ProviderConnection | None:
    if not connection_id:
        return None
    connection = await session.scalar(
        select(ProviderConnection).where(ProviderConnection.id == connection_id, ProviderConnection.user_id == user_id)
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    return connection


async def ensure_agent_role(session: AsyncSession, slug: str | None) -> AgentRole | None:
    if slug is None:
        return None
    role = await session.scalar(select(AgentRole).where(AgentRole.slug == slug))
    if not role:
        raise HTTPException(status_code=404, detail="Agent role not found")
    return role


async def get_skill_for_user(session: AsyncSession, *, skill_id: str, user_id: str) -> SkillDefinition | None:
    return await session.scalar(
        select(SkillDefinition)
        .options(selectinload(SkillDefinition.provider_connection))
        .join(Workspace, SkillDefinition.workspace_id == Workspace.id)
        .where(SkillDefinition.id == skill_id, Workspace.owner_id == user_id)
    )


async def get_workspace_for_user(session: AsyncSession, *, workspace_id: str, user_id: str) -> Workspace | None:
    return await session.scalar(select(Workspace).where(Workspace.id == workspace_id, Workspace.owner_id == user_id))


async def get_or_create_skill_conversation(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    skill: SkillDefinition,
    conversation_id: str | None,
) -> Conversation:
    conversation = None
    if conversation_id:
        conversation = await session.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.workspace_id == workspace.id))
    if conversation:
        return conversation

    conversation = Conversation(
        id=generate_entity_id("conversation"),
        workspace_id=workspace.id,
        title=f"{skill.name} Session",
        created_by_id=user.id,
        provider_id=skill.provider_id or workspace.default_provider_id,
        model_id=skill.model_id or workspace.default_model_id,
        provider_connection_id=skill.provider_connection_id or workspace.default_provider_connection_id,
        model_name=skill.model_name or workspace.default_model_name,
        use_knowledge=skill.use_knowledge,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


def render_skill_prompt(skill: SkillDefinition, variables: dict[str, str] | None) -> str:
    resolved_variables = defaultdict(str, variables or {})
    if not resolved_variables.get("input"):
        resolved_variables["input"] = "Provide an operational summary."
    return Formatter().vformat(skill.prompt_template, (), resolved_variables)


def build_cli_response_text(command: str, stdout: str, stderr: str, exit_code: int, cwd: str | None) -> str:
    parts = [f"CLI skill executed.\n\nCommand:\n{command}"]
    if cwd:
        parts.append(f"\nWorking directory:\n{cwd}")
    parts.append(f"\nExit code: {exit_code}")
    if stdout:
        parts.append(f"\nSTDOUT:\n{stdout}")
    if stderr:
        parts.append(f"\nSTDERR:\n{stderr}")
    return "\n".join(parts).strip()


def build_browser_response_text(actions: list[dict], extracted_text: str, current_url: str | None, title: str | None) -> str:
    parts = [f"Browser skill executed.\n\nActions:\n{json.dumps(actions, indent=2)}"]
    if current_url:
        parts.append(f"\nCurrent URL:\n{current_url}")
    if title:
        parts.append(f"\nPage title:\n{title}")
    if extracted_text:
        parts.append(f"\nExtracted text:\n{extracted_text}")
    return "\n".join(parts).strip()


@router.get("")
async def list_skills(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: str | None = Query(default=None),
):
    workspace = None
    runtimes = []
    machine_capabilities: list[dict] = []
    workspace_capabilities: list[dict] = []
    if workspace_id:
        workspace = await get_workspace_for_user(session, workspace_id=workspace_id, user_id=user.id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        runtimes = await list_runtimes_for_workspace(session, workspace.id)
        machine_capabilities = build_machine_capabilities(runtimes)
        workspace_status = build_workspace_readiness(workspace, runtimes)
        workspace_capabilities = list(workspace_status["capabilities"])

    statement = (
        select(SkillDefinition)
        .options(selectinload(SkillDefinition.provider_connection))
        .join(Workspace, SkillDefinition.workspace_id == Workspace.id)
        .where(Workspace.owner_id == user.id)
    )
    if workspace_id:
        statement = statement.where(SkillDefinition.workspace_id == workspace_id)
    result = await session.execute(statement.order_by(SkillDefinition.name.asc()))
    items = []
    for item in result.scalars().all():
        compatibility = None
        if workspace:
            compatibility = evaluate_skill_compatibility(
                item,
                machine_capabilities=machine_capabilities,
                workspace_capabilities=workspace_capabilities,
            )
        items.append(serialize_skill(item, compatibility=compatibility))
    return paginated_response(items)


@router.patch("/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: SkillUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    skill = await get_skill_for_user(session, skill_id=skill_id, user_id=user.id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if payload.enabled is not None:
        skill.enabled = payload.enabled
    if payload.skill_mode is not None:
        skill.skill_mode = payload.skill_mode
    if payload.required_runtime_type is not None:
        skill.required_runtime_type = payload.required_runtime_type or None
    if payload.session_mode is not None:
        skill.session_mode = payload.session_mode
    if payload.command_template is not None:
        skill.command_template = payload.command_template or None
    if payload.working_directory is not None:
        skill.working_directory = payload.working_directory or None
    if payload.agent_role_slug is not None:
        role = await ensure_agent_role(session, payload.agent_role_slug or None)
        skill.agent_role_slug = role.slug if role else None
    if payload.tool_capabilities is not None:
        skill.tool_capabilities = payload.tool_capabilities
    if payload.knowledge_scope is not None:
        skill.knowledge_scope = payload.knowledge_scope
    if payload.required_capabilities is not None:
        skill.required_capabilities = payload.required_capabilities
    if payload.recommended_capabilities is not None:
        skill.recommended_capabilities = payload.recommended_capabilities
    if payload.workspace_requirements is not None:
        skill.workspace_requirements = payload.workspace_requirements
    if payload.provider_connection_id is not None:
        connection = await ensure_provider_connection_for_user(session, connection_id=payload.provider_connection_id, user_id=user.id)
        skill.provider_connection_id = connection.id if connection else None
        skill.provider_connection = connection
    if payload.model_name is not None:
        skill.model_name = payload.model_name or None
    if payload.allow_model_override is not None:
        skill.allow_model_override = payload.allow_model_override
    if payload.use_knowledge is not None:
        skill.use_knowledge = payload.use_knowledge

    if skill.skill_mode == "cli" and not skill.required_runtime_type:
        skill.required_runtime_type = "cli"
    if skill.skill_mode == "browser" and not skill.required_runtime_type:
        skill.required_runtime_type = "browser"
    if skill.skill_mode == "prompt":
        skill.required_runtime_type = None

    await session.commit()
    await session.refresh(skill)
    runtimes = await list_runtimes_for_workspace(session, skill.workspace_id)
    workspace = await get_workspace_for_user(session, workspace_id=skill.workspace_id, user_id=user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    machine_capabilities = build_machine_capabilities(runtimes)
    workspace_status = build_workspace_readiness(workspace, runtimes)
    compatibility = evaluate_skill_compatibility(
        skill,
        machine_capabilities=machine_capabilities,
        workspace_capabilities=list(workspace_status["capabilities"]),
    )
    return success_response(serialize_skill(skill, compatibility=compatibility))


@router.post("/{skill_id}/run")
async def run_skill(
    skill_id: str,
    payload: SkillRunRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    skill = await get_skill_for_user(session, skill_id=skill_id, user_id=user.id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if not skill.enabled:
        raise HTTPException(status_code=400, detail="Skill is disabled")

    workspace = await get_workspace_for_user(session, workspace_id=payload.workspace_id, user_id=user.id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    runtimes = await list_runtimes_for_workspace(session, workspace.id)
    machine_capabilities = build_machine_capabilities(runtimes)
    workspace_status = build_workspace_readiness(workspace, runtimes)
    compatibility = SkillCompatibilityStatus.model_validate(
        evaluate_skill_compatibility(
            skill,
            machine_capabilities=machine_capabilities,
            workspace_capabilities=list(workspace_status["capabilities"]),
        )
    )
    if compatibility.status == "blocked":
        reasons = compatibility.missing_required_capabilities + compatibility.missing_workspace_requirements
        detail = ", ".join(reasons) if reasons else "required environment capabilities"
        raise HTTPException(status_code=400, detail=f"Skill is blocked by the local environment: {detail}")

    conversation = await get_or_create_skill_conversation(
        session,
        workspace=workspace,
        user=user,
        skill=skill,
        conversation_id=payload.conversation_id,
    )

    if skill.skill_mode == "cli":
        if not skill.command_template:
            raise HTTPException(status_code=400, detail="CLI skill is missing a command template")
        variables = {
            **(payload.variables or {}),
            "workspace_root": workspace.workspace_root_path or "",
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
        }
        rendered_command = render_template(skill.command_template or "", variables)
        working_directory = render_template(skill.working_directory or ".", variables)
        user_message = Message(
            id=generate_message_id("user"),
            conversation_id=conversation.id,
            role="user",
            content=f"Execute CLI skill '{skill.name}'.\n\nCommand template:\n{rendered_command}",
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        execution = await create_runtime_execution(
            session,
            workspace_id=workspace.id,
            user_id=user.id,
            source="skill",
            execution_kind="skill_cli",
            provider_id=conversation.provider_id,
            model_id=conversation.model_id,
            provider_connection_id=conversation.provider_connection_id,
            resolved_model_name=conversation.model_name,
            conversation_id=conversation.id,
            skill_id=skill.id,
            command_preview=rendered_command[:400],
            details_json={"working_directory": working_directory, "agent_role_slug": skill.agent_role_slug},
        )

        try:
            await mark_runtime_running(session, execution)
            result = await dispatch_cli_execution(
                session,
                workspace=workspace,
                user=user,
                execution=execution,
                skill=skill,
                command=rendered_command,
                working_directory=working_directory,
            )
            response_text = build_cli_response_text(
                rendered_command,
                result.get("stdout") or "",
                result.get("stderr") or "",
                int(result.get("exit_code") or 0),
                result.get("cwd"),
            )
            assistant_message = Message(
                id=generate_message_id("assistant"),
                conversation_id=conversation.id,
                runtime_execution_id=execution.id,
                role="assistant",
                content=response_text,
                sources_json=None,
            )
            session.add(assistant_message)
            await session.commit()
            await session.refresh(assistant_message)
            details = {
                "exit_code": result.get("exit_code"),
                "stderr": (result.get("stderr") or "")[:2000],
                "cwd": result.get("cwd"),
                "stdout": (result.get("stdout") or "")[:2000],
            }
            if int(result.get("exit_code") or 0) == 0:
                await mark_runtime_succeeded(
                    session,
                    execution,
                    response_preview=response_text[:2000],
                    details_json=details,
                    artifacts_json=result.get("artifacts_json"),
                )
            else:
                await mark_runtime_failed(
                    session,
                    execution,
                    error_message=(result.get("stderr") or result.get("stdout") or "CLI command failed"),
                    details_json=details,
                    artifacts_json=result.get("artifacts_json"),
                )
        except Exception as exc:
            await mark_runtime_failed(session, execution, error_message=str(exc))
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        response = SkillRunResponse(
            conversation=ConversationOut.model_validate(conversation),
            execution=RuntimeExecutionOut.model_validate(execution),
            user_message=MessageOut.model_validate(user_message),
            assistant_message=MessageOut.model_validate(assistant_message),
        )
        return success_response(response.model_dump())

    if skill.skill_mode == "browser":
        if not skill.command_template:
            raise HTTPException(status_code=400, detail="Browser skill is missing an action template")
        variables = {
            **(payload.variables or {}),
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
        }
        rendered_actions = render_template(skill.command_template, variables)
        try:
            actions = json.loads(rendered_actions)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Browser skill rendered invalid JSON: {exc}") from exc

        user_message = Message(
            id=generate_message_id("user"),
            conversation_id=conversation.id,
            role="user",
            content=f"Execute browser skill '{skill.name}'.\n\nAction template:\n{rendered_actions}",
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        execution = await create_runtime_execution(
            session,
            workspace_id=workspace.id,
            user_id=user.id,
            source="skill",
            execution_kind="skill_browser",
            provider_id=conversation.provider_id,
            model_id=conversation.model_id,
            provider_connection_id=conversation.provider_connection_id,
            resolved_model_name=conversation.model_name,
            conversation_id=conversation.id,
            skill_id=skill.id,
            command_preview=json.dumps(actions),
            details_json={"agent_role_slug": skill.agent_role_slug},
        )

        try:
            await mark_runtime_running(session, execution)
            result = await dispatch_browser_execution(
                session,
                workspace=workspace,
                user=user,
                execution=execution,
                skill=skill,
                actions=actions,
            )
            response_text = build_browser_response_text(
                actions,
                result.get("extracted_text") or "",
                result.get("current_url"),
                result.get("title"),
            )
            assistant_message = Message(
                id=generate_message_id("assistant"),
                conversation_id=conversation.id,
                runtime_execution_id=execution.id,
                role="assistant",
                content=response_text,
                sources_json=None,
            )
            session.add(assistant_message)
            await session.commit()
            await session.refresh(assistant_message)
            await mark_runtime_succeeded(
                session,
                execution,
                response_preview=response_text[:2000],
                details_json={
                    "current_url": result.get("current_url"),
                    "title": result.get("title"),
                    "extracted_text": (result.get("extracted_text") or "")[:2000],
                },
                artifacts_json=result.get("artifacts_json"),
            )
        except Exception as exc:
            await mark_runtime_failed(session, execution, error_message=str(exc))
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        response = SkillRunResponse(
            conversation=ConversationOut.model_validate(conversation),
            execution=RuntimeExecutionOut.model_validate(execution),
            user_message=MessageOut.model_validate(user_message),
            assistant_message=MessageOut.model_validate(assistant_message),
        )
        return success_response(response.model_dump())

    rendered_prompt = render_skill_prompt(skill, payload.variables)
    user_message = Message(id=generate_message_id("user"), conversation_id=conversation.id, role="user", content=rendered_prompt)
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    resolved = await resolve_conversation_context(session, conversation, user_id=user.id)
    retrieved_knowledge = None
    use_knowledge = payload.use_knowledge if payload.use_knowledge is not None else skill.use_knowledge
    if use_knowledge:
        retrieved_knowledge = await retrieve_relevant_chunks(session, workspace_id=workspace.id, query=rendered_prompt, user_id=user.id)

    llm_messages = await build_llm_messages(
        session,
        conversation,
        rendered_prompt,
        retrieved_knowledge,
        additional_system_prompt=f"This response is being generated from the skill '{skill.name}'. {skill.description}",
    )

    execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="skill",
        execution_kind="skill_prompt",
        provider_id=resolved.provider.id if resolved.provider else None,
        model_id=resolved.model.id if resolved.model else None,
        provider_connection_id=resolved.provider_connection.provider_connection_id,
        resolved_model_name=resolved.model_name,
        resolved_base_url=resolved.provider_connection.base_url,
        conversation_id=conversation.id,
        skill_id=skill.id,
        prompt_preview=rendered_prompt[:400],
        details_json=summarize_details(retrieved_knowledge),
    )

    try:
        await mark_runtime_running(session, execution)
        adapter = OpenAICompatibleProviderAdapter(
            api_key=resolved.provider_connection.api_key,
            base_url=resolved.provider_connection.base_url,
        )
        completion = await adapter.complete_chat(resolved.model_name, llm_messages)
        assistant_message = Message(
            id=generate_message_id("assistant"),
            conversation_id=conversation.id,
            runtime_execution_id=execution.id,
            role="assistant",
            content=completion.content,
            sources_json=serialize_sources(retrieved_knowledge),
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=completion.content[:400],
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
            details_json=summarize_details(retrieved_knowledge),
        )
    except Exception as exc:
        await mark_runtime_failed(session, execution, error_message=str(exc), details_json=summarize_details(retrieved_knowledge))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    response = SkillRunResponse(
        conversation=ConversationOut.model_validate(conversation),
        execution=RuntimeExecutionOut.model_validate(execution),
        user_message=MessageOut.model_validate(user_message),
        assistant_message=MessageOut.model_validate(assistant_message),
    )
    return success_response(response.model_dump())
