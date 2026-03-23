# DreamAxis v0.1.0

**Local-first runtime + skill + knowledge foundation**

DreamAxis is an open-source, self-hosted agent execution platform built for operators who want more than a chat box.

This first public release establishes the foundation:

- **no-signup by default**
- **OpenAI-compatible provider connections**
- **CLI Runtime**
- **Browser Runtime (Playwright)**
- **builtin skill packs**
- **builtin knowledge packs**
- **runtime/session/execution visibility**

## What ships in v0.1.0

### Local-first by default

DreamAxis defaults to:

```env
AUTH_MODE=local_open
```

That means:

- no public registration flow
- no hosted account dependency
- local bootstrap session for the default operator path
- metadata stored in your own PostgreSQL
- provider keys stored in your own deployment

### Real execution, not only chat

DreamAxis already includes two execution surfaces:

- **CLI Runtime v1** for workspace-safe command execution
- **Browser Runtime v1** for Playwright-based browser actions and screenshot artifacts

The runtime console exposes:

- runtime hosts
- sessions
- executions
- artifacts
- status history

### Skills as reusable assets

Builtin skill packs include:

- `core-cli`
- `core-browser-playwright`
- `core-research`
- `core-docs`
- `core-knowledge`
- `core-repo`

### Knowledge as a system layer

Builtin knowledge packs include:

- Playwright
- Git
- Docker
- Python
- TypeScript
- FastAPI
- Next.js
- DreamAxis architecture

You can also:

- upload `txt`, `md`, and `pdf`
- sync builtin docs
- use knowledge in chat and skill flows

## Product boundaries in this release

DreamAxis v0.1.0 is intentionally **not**:

- a hosted SaaS
- a forced public-signup product
- a full multi-agent DAG orchestrator
- a multi-vendor native SDK matrix

This release focuses on a strong base:

- local-first auth
- provider connection management
- runtime execution
- skill packs
- knowledge packs

## First-run flow

1. copy `.env.example` to `.env`
2. run Docker Compose
3. enter directly in `local_open`
4. add an OpenAI-compatible API key
5. run a CLI skill
6. run a Browser skill
7. sync builtin knowledge packs
8. upload a document
9. send a knowledge-enabled chat message
10. inspect runtime history

## Docs

- [README.md](../README.md)
- [architecture.md](./architecture.md)
- [development.md](./development.md)
- [deployment-modes.md](./deployment-modes.md)
- [skill-packs.md](./skill-packs.md)
- [knowledge-packs.md](./knowledge-packs.md)
- [browser-runtime.md](./browser-runtime.md)
- [screenshots.md](./screenshots.md)
- [ROADMAP.md](../ROADMAP.md)

## Thanks

This release is the start of a more open execution platform:

- local-first
- self-hosted
- runtime-centric
- skill-extensible
- knowledge-aware
