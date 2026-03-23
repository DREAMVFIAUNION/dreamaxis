# DreamAxis Knowledge Packs

Knowledge Packs promote docs from “uploaded files” to reusable knowledge assets.

## Source types

DreamAxis knowledge currently tracks four source categories:

- `user_upload`
- `builtin_pack`
- `git_repo`
- `web_capture`

Today, builtin pack sync and user upload are implemented. The other source types are reserved for the next expansion wave.

## Why packs exist

Knowledge in DreamAxis is not only for chat. It should also support:

- role-specific workflows
- runtime-assisted skills
- repo/document analysis
- durable system context for future agent orchestration

## Builtin packs shipped today

- `playwright-runtime`
- `git-playbook`
- `docker-ops`
- `python-notes`
- `typescript-runtime`
- `fastapi-notes`
- `nextjs-notes`
- `dreamaxis-architecture`

These packs seed local instances with useful baseline docs before the user uploads anything.

## Retrieval scope

DreamAxis retrieval is designed around three layers:

1. workspace documents
2. builtin knowledge packs
3. optional skill-attached knowledge scopes

That makes it possible to:

- ask general workspace questions
- run browser/CLI skills with attached operational docs
- attach role defaults such as Builder → Playwright/Git or Analyst → architecture notes

## Current ingestion behavior

### Builtin knowledge packs

During API startup and manual sync:

- manifests are loaded from the repo
- documents are written into `knowledge_documents`
- embeddings are attempted if a usable embedding connection exists
- if embeddings are not available, documents still sync and remain visible

Fallback behavior when embeddings are unavailable:

- document `status` becomes `ready`
- `chunk_count` may stay `0`
- `error_message` explains that embeddings were deferred

### User uploads

Supported file types:

- `.txt`
- `.md`
- `.pdf`

Files are saved under:

- `KNOWLEDGE_STORAGE_PATH`

Metadata is saved in PostgreSQL.

## API

### List documents

`GET /api/v1/knowledge?workspace_id=workspace-main`

Optional filters:

- `source_type`
- `knowledge_pack_slug`

### Upload document

`POST /api/v1/knowledge/upload`

### List packs

`GET /api/v1/knowledge-packs?workspace_id=workspace-main`

### Sync builtin packs

`POST /api/v1/knowledge-packs/sync?workspace_id=workspace-main`

## UI workflow

Open `/knowledge` to:

1. upload workspace files
2. sync builtin packs
3. filter by source type
4. inspect indexing state and chunk counts
5. confirm builtin docs are available for retrieval

## Near-term direction

Next logical extensions:

- repo-backed knowledge sources
- captured web docs
- re-index actions
- richer pack-level scope binding per skill and role
