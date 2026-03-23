# DreamAxis GitHub Release Template

Use this as the first public release note template for GitHub.

---

## DreamAxis v0.1.0 - Local-first runtime + skill + knowledge foundation

DreamAxis is an open-source, self-hosted agent execution platform built around:

- **no-signup by default**
- **OpenAI-compatible provider connections**
- **CLI Runtime**
- **Browser Runtime (Playwright)**
- **builtin skill packs**
- **builtin knowledge packs**

### Highlights

#### Local-first by default

- default deployment mode is `AUTH_MODE=local_open`
- no public registration flow is required for a local install
- user/workspace/provider/runtime metadata stays in your own PostgreSQL
- provider API keys remain self-hosted

#### Runtime execution layer

- CLI runtime host with reusable workspace-scoped sessions
- Browser runtime host with Playwright actions and screenshot artifacts
- runtime/session/execution visibility in the web console

#### Skill packs

Builtin packs currently include:

- `core-cli`
- `core-browser-playwright`
- `core-research`
- `core-docs`
- `core-knowledge`
- `core-repo`

#### Knowledge packs

Builtin packs currently include:

- Playwright
- Git
- Docker
- Python
- TypeScript
- FastAPI
- Next.js
- DreamAxis architecture notes

### Included routes

- `/dashboard`
- `/chat/[conversationId]`
- `/skills`
- `/knowledge`
- `/runtime`
- `/settings/providers`

### First-run path

1. copy `.env.example` to `.env`
2. run Docker Compose
3. enter directly in `local_open`
4. add an OpenAI-compatible API key
5. run a CLI skill
6. run a Browser skill
7. sync builtin knowledge packs
8. upload a document
9. send a knowledge-enabled chat message

### Notes

- this release is intentionally **not** a hosted SaaS product
- `password` mode exists for shared/private deployments, but `local_open` remains the default
- native Anthropic / Gemini protocol adapters are not included yet
- full multi-agent orchestration is not included yet

### Docs

- [README.md](../README.md)
- [development.md](./development.md)
- [deployment-modes.md](./deployment-modes.md)
- [skill-packs.md](./skill-packs.md)
- [knowledge-packs.md](./knowledge-packs.md)
- [browser-runtime.md](./browser-runtime.md)
- [release-checklist.md](./release-checklist.md)

### Screenshots

See [screenshots.md](./screenshots.md).
