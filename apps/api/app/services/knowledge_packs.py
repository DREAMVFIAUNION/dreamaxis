from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.knowledge_pack import KnowledgePack
from app.models.workspace import Workspace
from app.services.assistant_service import generate_entity_id
from app.services.chat_service import resolve_workspace_embedding_context
from app.services.knowledge_service import SUPPORTED_TYPES, build_embedding_error_message, chunk_text, normalize_text
from app.services.llm_provider import OpenAICompatibleProviderAdapter

BUILTIN_KNOWLEDGE_PACKS_DIR = Path(__file__).resolve().parents[1] / "builtin" / "knowledge_packs"
settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def pack_id_for_slug(slug: str) -> str:
    return f"knowledge-pack-{slug}"[:64]


def document_id_for_slug(slug: str) -> str:
    return f"doc-{slug}"[:64]


def builtin_knowledge_pack_manifests() -> list[Path]:
    if not BUILTIN_KNOWLEDGE_PACKS_DIR.exists():
        return []
    return sorted(BUILTIN_KNOWLEDGE_PACKS_DIR.glob("*.json"))


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


async def _sync_document(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user_id: str,
    pack: KnowledgePack,
    doc_manifest: dict,
) -> KnowledgeDocument:
    source_file = (BUILTIN_KNOWLEDGE_PACKS_DIR / doc_manifest["path"]).resolve()
    suffix = source_file.suffix.lower()
    file_type = SUPPORTED_TYPES.get(suffix, "markdown")
    file_name = doc_manifest.get("file_name") or source_file.name
    title = doc_manifest.get("title") or source_file.stem.replace("-", " ").title()
    storage_dir = settings.knowledge_storage_dir / workspace.id / "builtin" / pack.slug
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / file_name
    content = source_file.read_text(encoding="utf-8")
    storage_path.write_text(content, encoding="utf-8")

    document = await session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace.id,
            KnowledgeDocument.knowledge_pack_slug == pack.slug,
            KnowledgeDocument.file_name == file_name,
        )
    )
    if not document:
        document = KnowledgeDocument(
            id=document_id_for_slug(f"{pack.slug}-{source_file.stem}"),
            workspace_id=workspace.id,
            file_name=file_name,
            title=title,
            file_type=file_type,
            status="processing",
            source_type="builtin_pack",
            source_ref=doc_manifest["path"],
            knowledge_pack_slug=pack.slug,
            storage_path=str(storage_path),
        )
        session.add(document)
        await session.flush()

    document.title = title
    document.file_type = file_type
    document.status = "processing"
    document.source_type = "builtin_pack"
    document.source_ref = doc_manifest["path"]
    document.knowledge_pack_slug = pack.slug
    document.storage_path = str(storage_path)
    document.error_message = None

    await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))

    extracted_text = normalize_text(content)
    chunks = chunk_text(extracted_text)
    document.content_length = len(extracted_text)
    document.chunk_count = 0

    try:
        if chunks:
            embedding_context = await resolve_workspace_embedding_context(session, workspace, user_id=user_id)
            adapter = OpenAICompatibleProviderAdapter(
                api_key=embedding_context.provider_connection.api_key,
                base_url=embedding_context.provider_connection.base_url,
            )
            embeddings = await adapter.embed_texts(chunks, embedding_context.model_name)
            session.add_all(
                [
                    KnowledgeChunk(
                        id=generate_entity_id("chunk"),
                        document_id=document.id,
                        workspace_id=workspace.id,
                        chunk_index=index,
                        content=chunk,
                        token_count=max(1, len(chunk) // 4),
                        embedding=embedding,
                    )
                    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
                ]
            )
            document.chunk_count = len(chunks)
        document.status = "ready"
    except Exception as exc:
        document.status = "ready"
        document.error_message = build_embedding_error_message(exc, deferred=True)

    return document


async def sync_builtin_knowledge_packs(session: AsyncSession, workspace: Workspace, *, user_id: str) -> tuple[int, int]:
    synced_packs = 0
    synced_docs = 0
    for manifest_path in builtin_knowledge_pack_manifests():
        manifest = load_manifest(manifest_path)
        pack = await session.scalar(select(KnowledgePack).where(KnowledgePack.slug == manifest["slug"], KnowledgePack.workspace_id == workspace.id))
        if not pack:
            pack = KnowledgePack(id=pack_id_for_slug(manifest["slug"]), workspace_id=workspace.id, slug=manifest["slug"])
            session.add(pack)
        pack.name = manifest["name"]
        pack.version = manifest.get("version", "1.0.0")
        pack.description = manifest.get("description", "")
        pack.source_type = "builtin_pack"
        pack.source_ref = f"builtin://{manifest['slug']}"
        pack.manifest_path = str(manifest_path)
        pack.is_builtin = True
        pack.status = "synced"
        pack.last_synced_at = utcnow()
        await session.flush()

        for doc_manifest in manifest.get("documents", []):
            await _sync_document(session, workspace=workspace, user_id=user_id, pack=pack, doc_manifest=doc_manifest)
            synced_docs += 1
        synced_packs += 1

    await session.commit()
    return synced_packs, synced_docs
