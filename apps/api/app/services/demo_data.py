from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import encrypt_secret, get_password_hash
from app.models.agent_role import AgentRole
from app.models.ai_model import AIModel
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.provider import Provider
from app.models.provider_connection import ProviderConnection
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace

settings = get_settings()

DEMO_USER_ID = "user-demo"
DEMO_WORKSPACE_ID = "workspace-main"
DEMO_CONVERSATION_ID = "local-demo"
OPENAI_PROVIDER_ID = "provider-openai"
OPENAI_CHAT_MODEL_ID = "model-openai-chat"
OPENAI_EMBED_MODEL_ID = "model-openai-embedding"
DEMO_CONNECTION_ID = "conn-demo-openai-compatible"


async def seed_demo_data(session: AsyncSession) -> None:
    existing_user = await session.scalar(select(User).where(User.id == DEMO_USER_ID))
    if not existing_user:
        session.add(
            User(
                id=DEMO_USER_ID,
                email="demo@dreamaxis.dev",
                full_name="DreamAxis Operator",
                password_hash=get_password_hash("dreamaxis"),
            )
        )

    provider_by_slug = await session.scalar(select(Provider).where(Provider.slug == "openai-compatible"))
    provider_by_id = await session.scalar(select(Provider).where(Provider.id == OPENAI_PROVIDER_ID))
    provider = provider_by_slug or provider_by_id
    provider_status = "active"
    if not provider:
        session.add(Provider(id=OPENAI_PROVIDER_ID, slug="openai-compatible", name="OpenAI-Compatible", type="openai_compatible", status=provider_status))
        provider_id = OPENAI_PROVIDER_ID
    else:
        if provider is provider_by_id and provider_by_slug and provider_by_slug.id != provider_by_id.id:
            provider = provider_by_slug
        provider.slug = "openai-compatible"
        provider.name = "OpenAI-Compatible"
        provider.type = "openai_compatible"
        provider.status = provider_status
        provider_id = provider.id

    chat_model = await session.scalar(select(AIModel).where(AIModel.id == OPENAI_CHAT_MODEL_ID))
    if not chat_model:
        session.add(
            AIModel(
                id=OPENAI_CHAT_MODEL_ID,
                provider_id=provider_id,
                slug=settings.OPENAI_CHAT_MODEL,
                name="Default Chat Model",
                kind="chat",
                context_window=128000,
                is_default=True,
            )
        )
    else:
        chat_model.provider_id = provider_id
        chat_model.slug = settings.OPENAI_CHAT_MODEL
        chat_model.name = "Default Chat Model"
        chat_model.kind = "chat"
        chat_model.is_default = True

    embed_model = await session.scalar(select(AIModel).where(AIModel.id == OPENAI_EMBED_MODEL_ID))
    if not embed_model:
        session.add(
            AIModel(
                id=OPENAI_EMBED_MODEL_ID,
                provider_id=provider_id,
                slug=settings.OPENAI_EMBEDDING_MODEL,
                name="Default Embedding Model",
                kind="embedding",
                context_window=settings.OPENAI_EMBEDDING_DIMENSIONS,
                is_default=True,
            )
        )
    else:
        embed_model.provider_id = provider_id
        embed_model.slug = settings.OPENAI_EMBEDDING_MODEL
        embed_model.name = "Default Embedding Model"
        embed_model.kind = "embedding"
        embed_model.is_default = True

    connection = await session.scalar(select(ProviderConnection).where(ProviderConnection.id == DEMO_CONNECTION_ID))
    api_key_encrypted = encrypt_secret(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    connection_status = "active" if settings.OPENAI_API_KEY else "requires_config"
    connection_models = [
        {"name": settings.OPENAI_CHAT_MODEL, "kind": "chat", "source": "manual"},
        {"name": settings.OPENAI_EMBEDDING_MODEL, "kind": "embedding", "source": "manual"},
    ]
    if not connection:
        session.add(
            ProviderConnection(
                id=DEMO_CONNECTION_ID,
                user_id=DEMO_USER_ID,
                provider_id=provider_id,
                provider_type="openai_compatible",
                name="Local OpenAI-Compatible",
                base_url=(settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/"),
                api_key_encrypted=api_key_encrypted,
                model_discovery_mode="auto",
                status=connection_status,
                default_model_name=settings.OPENAI_CHAT_MODEL,
                default_embedding_model_name=settings.OPENAI_EMBEDDING_MODEL,
                discovered_models_json=connection_models,
            )
        )
    else:
        connection.provider_id = provider_id
        connection.provider_type = "openai_compatible"
        connection.name = "Local OpenAI-Compatible"
        connection.base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        connection.api_key_encrypted = api_key_encrypted
        connection.model_discovery_mode = "auto"
        connection.status = connection_status
        connection.default_model_name = settings.OPENAI_CHAT_MODEL
        connection.default_embedding_model_name = settings.OPENAI_EMBEDDING_MODEL
        connection.discovered_models_json = connection_models
        connection.is_enabled = True

    workspace = await session.scalar(select(Workspace).where(Workspace.id == DEMO_WORKSPACE_ID))
    if not workspace:
        session.add(
            Workspace(
                id=DEMO_WORKSPACE_ID,
                name="DreamAxis Core",
                slug="dreamaxis-core",
                description="Primary local execution workspace",
                owner_id=DEMO_USER_ID,
                workspace_root_path=str(settings.workspace_root_base_dir),
                default_provider_id=provider_id,
                default_model_id=OPENAI_CHAT_MODEL_ID,
                default_provider_connection_id=DEMO_CONNECTION_ID,
                default_model_name=settings.OPENAI_CHAT_MODEL,
                default_embedding_model_name=settings.OPENAI_EMBEDDING_MODEL,
            )
        )
    else:
        workspace.workspace_root_path = workspace.workspace_root_path or str(settings.workspace_root_base_dir)
        workspace.default_provider_id = provider_id
        workspace.default_model_id = OPENAI_CHAT_MODEL_ID
        workspace.default_provider_connection_id = DEMO_CONNECTION_ID
        workspace.default_model_name = settings.OPENAI_CHAT_MODEL
        workspace.default_embedding_model_name = settings.OPENAI_EMBEDDING_MODEL

    conversation = await session.scalar(select(Conversation).where(Conversation.id == DEMO_CONVERSATION_ID))
    if not conversation:
        session.add(
            Conversation(
                id=DEMO_CONVERSATION_ID,
                workspace_id=DEMO_WORKSPACE_ID,
                title="Initial Command Lane",
                created_by_id=DEMO_USER_ID,
                provider_id=provider_id,
                model_id=OPENAI_CHAT_MODEL_ID,
                provider_connection_id=DEMO_CONNECTION_ID,
                model_name=settings.OPENAI_CHAT_MODEL,
                use_knowledge=True,
            )
        )
    else:
        conversation.provider_id = provider_id
        conversation.model_id = OPENAI_CHAT_MODEL_ID
        conversation.provider_connection_id = DEMO_CONNECTION_ID
        conversation.model_name = settings.OPENAI_CHAT_MODEL
        conversation.use_knowledge = True

    existing_message = await session.scalar(select(Message).where(Message.id == "message-seed"))
    if not existing_message:
        session.add(
            Message(
                id="message-seed",
                conversation_id=DEMO_CONVERSATION_ID,
                role="assistant",
                content="DreamAxis command lane is online. Add or edit a provider connection, sync models, and stream through any OpenAI-compatible endpoint.",
            )
        )

    agent_roles = [
        {
            "slug": "commander",
            "name": "Commander",
            "system_prompt": "Coordinate execution, delegate intent, and keep DreamAxis aligned to operator goals.",
            "allowed_skill_modes": ["prompt"],
            "allowed_runtime_types": [],
            "default_skill_pack_slugs": ["core-docs", "core-knowledge"],
            "default_knowledge_pack_slugs": ["dreamaxis-architecture"],
        },
        {
            "slug": "analyst",
            "name": "Analyst",
            "system_prompt": "Reason over knowledge, produce concise assessments, and surface risks or trends.",
            "allowed_skill_modes": ["prompt"],
            "allowed_runtime_types": [],
            "default_skill_pack_slugs": ["core-research", "core-knowledge"],
            "default_knowledge_pack_slugs": ["dreamaxis-architecture", "fastapi-notes", "nextjs-notes"],
        },
        {
            "slug": "builder",
            "name": "Builder",
            "system_prompt": "Use approved CLI skills to inspect repositories, prepare implementation context, and report actionable findings.",
            "allowed_skill_modes": ["prompt", "cli", "browser"],
            "allowed_runtime_types": ["cli", "browser"],
            "default_skill_pack_slugs": ["core-cli", "core-browser-playwright", "core-repo", "core-docs", "core-knowledge"],
            "default_knowledge_pack_slugs": ["dreamaxis-architecture", "playwright-runtime", "git-playbook"],
        },
        {
            "slug": "operator",
            "name": "Operator",
            "system_prompt": "Execute controlled operational commands inside workspace-safe runtime sessions and capture artifacts.",
            "allowed_skill_modes": ["prompt", "cli", "browser"],
            "allowed_runtime_types": ["cli", "browser"],
            "default_skill_pack_slugs": ["core-cli", "core-browser-playwright"],
            "default_knowledge_pack_slugs": ["docker-ops", "playwright-runtime"],
        },
        {
            "slug": "archivist",
            "name": "Archivist",
            "system_prompt": "Summarize history, preserve operational context, and maintain a durable record of changes.",
            "allowed_skill_modes": ["prompt"],
            "allowed_runtime_types": [],
            "default_skill_pack_slugs": ["core-docs", "core-knowledge"],
            "default_knowledge_pack_slugs": ["dreamaxis-architecture", "python-notes"],
        },
        {
            "slug": "sentinel",
            "name": "Sentinel",
            "system_prompt": "Audit executions, validate policy boundaries, and flag anomalous or unsafe behavior.",
            "allowed_skill_modes": ["prompt"],
            "allowed_runtime_types": [],
            "default_skill_pack_slugs": ["core-research"],
            "default_knowledge_pack_slugs": ["dreamaxis-architecture"],
        },
    ]

    for payload in agent_roles:
        role = await session.scalar(select(AgentRole).where(AgentRole.slug == payload["slug"]))
        if not role:
            session.add(
                AgentRole(
                    slug=payload["slug"],
                    name=payload["name"],
                    system_prompt=payload["system_prompt"],
                    allowed_skill_modes=payload["allowed_skill_modes"],
                    allowed_runtime_types=payload["allowed_runtime_types"],
                    default_skill_pack_slugs=payload["default_skill_pack_slugs"],
                    default_knowledge_pack_slugs=payload["default_knowledge_pack_slugs"],
                )
            )
        else:
            role.name = payload["name"]
            role.system_prompt = payload["system_prompt"]
            role.allowed_skill_modes = payload["allowed_skill_modes"]
            role.allowed_runtime_types = payload["allowed_runtime_types"]
            role.default_skill_pack_slugs = payload["default_skill_pack_slugs"]
            role.default_knowledge_pack_slugs = payload["default_knowledge_pack_slugs"]

    skills = [
        {
            "id": "skill-incident-brief",
            "name": "Incident Brief",
            "slug": "incident-brief",
            "description": "Summarize an incident or operational anomaly into a concise response brief.",
            "prompt_template": "Create an incident brief for the following situation:\n\n{input}\n\nReturn summary, impact, and next actions.",
            "skill_mode": "prompt",
            "required_runtime_type": None,
            "session_mode": "reuse",
            "command_template": None,
            "working_directory": None,
            "agent_role_slug": "analyst",
            "required_capabilities": [],
            "recommended_capabilities": ["git"],
            "workspace_requirements": [],
        },
        {
            "id": "skill-rag-summary",
            "name": "Knowledge Summary",
            "slug": "knowledge-summary",
            "description": "Summarize uploaded knowledge with operational recommendations.",
            "prompt_template": "Using the workspace knowledge base, summarize the topic below and extract the most actionable insights:\n\n{input}",
            "skill_mode": "prompt",
            "required_runtime_type": None,
            "session_mode": "reuse",
            "command_template": None,
            "working_directory": None,
            "agent_role_slug": "archivist",
            "required_capabilities": [],
            "recommended_capabilities": ["python"],
            "workspace_requirements": [],
        },
        {
            "id": "skill-repo-snapshot",
            "name": "Repo Snapshot",
            "slug": "repo-snapshot",
            "description": "Run a safe CLI inspection inside the workspace root and return the latest directory snapshot.",
            "prompt_template": "Inspect the workspace repository and summarize the current directory state.",
            "skill_mode": "cli",
            "required_runtime_type": "cli",
            "session_mode": "reuse",
            "command_template": "Get-ChildItem -Force",
            "working_directory": ".",
            "agent_role_slug": "operator",
            "required_capabilities": ["python"],
            "recommended_capabilities": ["git", "node"],
            "workspace_requirements": ["safe_root"],
        },
    ]
    for payload in skills:
        skill = await session.scalar(select(SkillDefinition).where(SkillDefinition.id == payload["id"]))
        if not skill:
            session.add(
                SkillDefinition(
                    id=payload["id"],
                    workspace_id=DEMO_WORKSPACE_ID,
                    name=payload["name"],
                    slug=payload["slug"],
                    description=payload["description"],
                    prompt_template=payload["prompt_template"],
                    input_schema={"input": {"type": "string", "label": "Input"}},
                    enabled=True,
                    skill_mode=payload["skill_mode"],
                    required_runtime_type=payload["required_runtime_type"],
                    session_mode=payload["session_mode"],
                    command_template=payload["command_template"],
                    working_directory=payload["working_directory"],
                    agent_role_slug=payload["agent_role_slug"],
                    required_capabilities=payload["required_capabilities"],
                    recommended_capabilities=payload["recommended_capabilities"],
                    workspace_requirements=payload["workspace_requirements"],
                    provider_id=provider_id,
                    model_id=OPENAI_CHAT_MODEL_ID,
                    provider_connection_id=DEMO_CONNECTION_ID,
                    model_name=settings.OPENAI_CHAT_MODEL,
                    allow_model_override=True,
                    use_knowledge=True,
                )
            )
        else:
            skill.name = payload["name"]
            skill.slug = payload["slug"]
            skill.description = payload["description"]
            skill.prompt_template = payload["prompt_template"]
            skill.enabled = True
            skill.skill_mode = payload["skill_mode"]
            skill.required_runtime_type = payload["required_runtime_type"]
            skill.session_mode = payload["session_mode"]
            skill.command_template = payload["command_template"]
            skill.working_directory = payload["working_directory"]
            skill.agent_role_slug = payload["agent_role_slug"]
            skill.required_capabilities = payload["required_capabilities"]
            skill.recommended_capabilities = payload["recommended_capabilities"]
            skill.workspace_requirements = payload["workspace_requirements"]
            skill.provider_id = provider_id
            skill.model_id = OPENAI_CHAT_MODEL_ID
            skill.provider_connection_id = DEMO_CONNECTION_ID
            skill.model_name = settings.OPENAI_CHAT_MODEL
            skill.allow_model_override = True
            skill.use_knowledge = True

    await session.commit()
