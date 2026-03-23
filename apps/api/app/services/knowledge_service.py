from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.workspace import Workspace
from app.schemas.message import KnowledgeChunkReference
from app.services.assistant_service import generate_entity_id
from app.services.chat_service import resolve_workspace_embedding_context
from app.services.llm_provider import OpenAICompatibleProviderAdapter

settings = get_settings()
SUPPORTED_TYPES = {".txt": "text", ".md": "markdown", ".pdf": "pdf"}
WHITESPACE_RE = re.compile(r"\s+")
API_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9*_-]+\b")


@dataclass
class RetrievedKnowledge:
    sources: list[KnowledgeChunkReference]
    context: str


def sanitize_provider_error_message(value: str) -> str:
    sanitized = API_KEY_RE.sub("[redacted-api-key]", value or "")
    return WHITESPACE_RE.sub(" ", sanitized).strip()


def build_embedding_error_message(exc: Exception, *, deferred: bool = False) -> str:
    raw = sanitize_provider_error_message(str(exc))
    lowered = raw.lower()

    if "no provider connection is configured for embeddings" in lowered:
        message = "Configure an embedding-capable provider connection in Provider Settings to index this knowledge source."
    elif "invalid_api_key" in lowered or "incorrect api key provided" in lowered or ("401" in lowered and "api key" in lowered):
        message = "Embeddings could not be created. Update the API key or embedding model in Provider Settings."
    elif "insufficient_quota" in lowered or "quota" in lowered or "billing" in lowered:
        message = "Embeddings could not be created because the provider account has no available quota."
    elif "connection error" in lowered or "timed out" in lowered or "temporarily unavailable" in lowered:
        message = "Embeddings could not be created because the provider connection is currently unavailable."
    else:
        message = "Embeddings could not be created. Check Provider Settings and runtime logs for more detail."

    return f"Embeddings deferred. {message}" if deferred else message


async def ingest_upload(session: AsyncSession, workspace: Workspace, upload_file: UploadFile, *, user_id: str) -> KnowledgeDocument:
    suffix = Path(upload_file.filename or "upload.txt").suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type. Only txt, md, and pdf are supported.")

    file_name = sanitize_file_name(upload_file.filename or f"document{suffix}")
    document_id = generate_entity_id("doc")
    storage_dir = settings.knowledge_storage_dir / workspace.id / document_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / file_name

    file_bytes = await upload_file.read()
    storage_path.write_bytes(file_bytes)

    document = KnowledgeDocument(
        id=document_id,
        workspace_id=workspace.id,
        file_name=file_name,
        title=Path(file_name).stem,
        file_type=SUPPORTED_TYPES[suffix],
        status="processing",
        source_type="user_upload",
        source_ref=upload_file.filename or file_name,
        storage_path=str(storage_path),
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    try:
        extracted_text = extract_text(storage_path, suffix)
        chunks = chunk_text(extracted_text)
        if not chunks:
            raise ValueError("No extractable text was found in the uploaded document")

        embedding_context = await resolve_workspace_embedding_context(session, workspace, user_id=user_id)
        adapter = OpenAICompatibleProviderAdapter(
            api_key=embedding_context.provider_connection.api_key,
            base_url=embedding_context.provider_connection.base_url,
        )
        embeddings = await adapter.embed_texts(chunks, embedding_context.model_name)

        rows = []
        for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            rows.append(
                KnowledgeChunk(
                    id=generate_entity_id("chunk"),
                    document_id=document.id,
                    workspace_id=workspace.id,
                    chunk_index=index,
                    content=content,
                    token_count=max(1, len(content) // 4),
                    embedding=embedding,
                )
            )
        session.add_all(rows)
        document.status = "ready"
        document.content_length = len(extracted_text)
        document.chunk_count = len(rows)
        document.error_message = None
    except Exception as exc:
        document.status = "failed"
        document.error_message = build_embedding_error_message(exc)

    await session.commit()
    await session.refresh(document)
    return document


async def retrieve_relevant_chunks(
    session: AsyncSession,
    *,
    workspace_id: str,
    query: str,
    user_id: str,
    top_k: int | None = None,
) -> RetrievedKnowledge:
    top_k = top_k or settings.KNOWLEDGE_TOP_K
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if workspace is None:
        return RetrievedKnowledge(sources=[], context="")

    existing_chunk = await session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == workspace_id).limit(1))
    if existing_chunk is None:
        return RetrievedKnowledge(sources=[], context="")

    embedding_context = await resolve_workspace_embedding_context(session, workspace, user_id=user_id)
    adapter = OpenAICompatibleProviderAdapter(
        api_key=embedding_context.provider_connection.api_key,
        base_url=embedding_context.provider_connection.base_url,
    )
    embedding = (await adapter.embed_texts([query], embedding_context.model_name))[0]
    distance = KnowledgeChunk.embedding.cosine_distance(embedding)
    statement = (
        select(KnowledgeChunk, KnowledgeDocument, distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeChunk.workspace_id == workspace_id)
        .where(KnowledgeDocument.status == "ready")
        .order_by(distance)
        .limit(top_k)
    )
    result = await session.execute(statement)

    sources = []
    context_blocks = []
    for chunk, document, score in result.all():
        similarity = max(0.0, 1.0 - float(score))
        sources.append(
            KnowledgeChunkReference(
                document_id=document.id,
                document_name=document.file_name,
                chunk_id=chunk.id,
                excerpt=shorten(chunk.content, 220),
                score=round(similarity, 4),
            )
        )
        context_blocks.append(f"[{document.file_name} / chunk {chunk.chunk_index}]\n{chunk.content}")

    return RetrievedKnowledge(sources=sources, context="\n\n".join(context_blocks))


def sanitize_file_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "document"


def extract_text(path: Path, suffix: str) -> str:
    if suffix in {".txt", ".md"}:
        return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return normalize_text("\n".join(pages))
    return ""


def normalize_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def chunk_text(value: str) -> list[str]:
    if not value:
        return []
    size = settings.KNOWLEDGE_CHUNK_SIZE
    overlap = settings.KNOWLEDGE_CHUNK_OVERLAP
    chunks: list[str] = []
    start = 0
    while start < len(value):
        end = min(len(value), start + size)
        chunk = value[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(value):
            break
        start = max(end - overlap, start + 1)
    return chunks


def shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."
