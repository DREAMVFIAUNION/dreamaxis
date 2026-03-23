# DreamAxis - Local-first runtime + skill + knowledge foundation

I just open-sourced **DreamAxis**, a local-first agent execution platform for self-hosted AI workflows.

The core idea is simple: AI tooling should not stop at chat. It should help users run real work locally, keep their own keys and data, and accumulate reusable execution assets over time.

## What DreamAxis does today

DreamAxis v0.1.0 already includes:

- **no-signup by default** via `AUTH_MODE=local_open`
- **OpenAI-compatible provider connections**
- **CLI Runtime**
- **Browser Runtime (Playwright)**
- **builtin skill packs**
- **builtin knowledge packs**
- **runtime/session/execution visibility**

It is built as a local-first monorepo with:

- Next.js web UI
- FastAPI backend
- PostgreSQL + pgvector
- Redis
- Docker Compose

## Why I made it

A lot of current AI products feel too closed:

- hosted by default
- account-gated by default
- weak on real execution
- weak on reusable local knowledge
- hard to adapt to your own runtime environment

DreamAxis is an attempt at a more open foundation:

- local-first
- runtime-centric
- self-hosted keys
- reusable skills
- reusable knowledge

## What makes it different

### 1. No-signup by default

DreamAxis does not assume a hosted identity layer for the normal path.

The default mode is:

```env
AUTH_MODE=local_open
```

That means you can start locally without building or adopting a public registration system first.

### 2. Execution, not only chat

The current release already supports:

- CLI Runtime for workspace-safe command execution
- Browser Runtime for Playwright-backed browser actions and artifacts

### 3. Skills and knowledge as assets

The system is designed so that:

- skill packs can be reused and extended
- knowledge packs can be synced and built on
- uploaded docs can become part of retrieval and operator workflows

## What this release is not

DreamAxis v0.1.0 is intentionally **not**:

- a hosted SaaS
- a fully autonomous multi-agent operating system
- a complete native adapter matrix for every AI vendor

This first public release is about the foundation.

## First-run flow

1. clone the repo
2. copy `.env.example` to `.env`
3. run Docker Compose
4. enter via `local_open`
5. add an OpenAI-compatible API key
6. run a CLI skill
7. run a Browser skill
8. sync builtin knowledge packs
9. upload a document
10. inspect `/runtime`

## Repo

- GitHub: https://github.com/DREAMVFIAUNION/dreamaxis
- Release: https://github.com/DREAMVFIAUNION/dreamaxis/releases/tag/v0.1.0

If you care about self-hosted AI workflows, local execution, or making AI tooling more open and reusable, I'd love feedback.
