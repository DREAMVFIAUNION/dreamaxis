from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_definition import SkillDefinition
from app.models.skill_pack import SkillPack
from app.models.workspace import Workspace

BUILTIN_SKILL_PACKS_DIR = Path(__file__).resolve().parents[1] / "builtin" / "skill_packs"
MANIFEST_FILE_NAMES = ("dreamaxis.skill-pack.json", "skill-pack.json")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def pack_id_for_slug(slug: str) -> str:
    return f"skill-pack-{slugify(slug)}"[:64]


def skill_id_for_slug(slug: str) -> str:
    return f"skill-{slugify(slug)}"[:64]


def load_skill_pack_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_manifest_path(source_path: str) -> Path:
    path = Path(source_path).expanduser().resolve()
    if path.is_file():
        return path
    if path.is_dir():
        for candidate in MANIFEST_FILE_NAMES:
            manifest = path / candidate
            if manifest.exists():
                return manifest
        manifests = sorted(path.glob("*.skill-pack.json"))
        if manifests:
            return manifests[0]
    raise HTTPException(status_code=404, detail="Skill pack manifest not found")


def builtin_skill_pack_manifests() -> list[Path]:
    if not BUILTIN_SKILL_PACKS_DIR.exists():
        return []
    return sorted(BUILTIN_SKILL_PACKS_DIR.glob("*.json"))


async def upsert_skill_pack_from_manifest(
    session: AsyncSession,
    *,
    workspace: Workspace,
    manifest: dict[str, Any],
    source_type: str,
    source_ref: str | None,
    manifest_path: str | None,
    is_builtin: bool,
) -> tuple[SkillPack, int]:
    slug = manifest["slug"]
    pack = await session.scalar(select(SkillPack).where(SkillPack.slug == slug, SkillPack.workspace_id == workspace.id))
    if not pack:
        pack = SkillPack(id=pack_id_for_slug(slug), workspace_id=workspace.id, slug=slug)
        session.add(pack)

    pack.name = manifest["name"]
    pack.version = manifest.get("version", "1.0.0")
    pack.description = manifest.get("description", "")
    pack.source_type = source_type
    pack.source_ref = source_ref
    pack.manifest_path = manifest_path
    pack.is_builtin = is_builtin
    pack.status = manifest.get("status", "synced")
    pack.tool_capabilities_json = manifest.get("tool_capabilities")
    pack.last_synced_at = utcnow()

    synced_skill_count = 0
    for entry in manifest.get("skills", []):
        skill = await session.scalar(
            select(SkillDefinition).where(SkillDefinition.workspace_id == workspace.id, SkillDefinition.slug == entry["slug"])
        )
        if not skill:
            skill = SkillDefinition(id=skill_id_for_slug(entry["slug"]), workspace_id=workspace.id, slug=entry["slug"])
            session.add(skill)
        skill.name = entry["name"]
        skill.description = entry.get("description", "")
        skill.prompt_template = entry.get("prompt_template", entry.get("description", entry["name"]))
        skill.input_schema = entry.get("input_schema") or {"input": {"type": "string", "label": "Input"}}
        skill.tool_capabilities = entry.get("tool_capabilities")
        skill.knowledge_scope = entry.get("knowledge_scope")
        skill.required_capabilities = entry.get("required_capabilities")
        skill.recommended_capabilities = entry.get("recommended_capabilities")
        skill.workspace_requirements = entry.get("workspace_requirements")
        skill.enabled = bool(entry.get("enabled", True))
        skill.skill_mode = entry.get("skill_mode", "prompt")
        skill.required_runtime_type = entry.get("required_runtime_type")
        skill.session_mode = entry.get("session_mode", "reuse")
        skill.command_template = entry.get("command_template")
        skill.working_directory = entry.get("working_directory")
        skill.agent_role_slug = entry.get("agent_role_slug")
        skill.pack_slug = pack.slug
        skill.pack_version = pack.version
        skill.is_builtin = is_builtin
        skill.provider_id = workspace.default_provider_id
        skill.model_id = workspace.default_model_id
        skill.provider_connection_id = workspace.default_provider_connection_id
        skill.model_name = entry.get("model_name") or workspace.default_model_name
        skill.allow_model_override = bool(entry.get("allow_model_override", True))
        skill.use_knowledge = bool(entry.get("use_knowledge", True))
        synced_skill_count += 1

    await session.commit()
    await session.refresh(pack)
    return pack, synced_skill_count


async def sync_builtin_skill_packs(session: AsyncSession, workspace: Workspace) -> tuple[int, int]:
    synced_packs = 0
    synced_skills = 0
    for manifest_path in builtin_skill_pack_manifests():
        manifest = load_skill_pack_manifest(manifest_path)
        _, count = await upsert_skill_pack_from_manifest(
            session,
            workspace=workspace,
            manifest=manifest,
            source_type="builtin",
            source_ref=f"builtin://{manifest['slug']}",
            manifest_path=str(manifest_path),
            is_builtin=True,
        )
        synced_packs += 1
        synced_skills += count
    return synced_packs, synced_skills


async def import_skill_pack(session: AsyncSession, workspace: Workspace, source_path: str) -> tuple[SkillPack, int]:
    manifest_path = resolve_manifest_path(source_path)
    manifest = load_skill_pack_manifest(manifest_path)
    return await upsert_skill_pack_from_manifest(
        session,
        workspace=workspace,
        manifest=manifest,
        source_type="imported",
        source_ref=str(manifest_path.parent),
        manifest_path=str(manifest_path),
        is_builtin=False,
    )
