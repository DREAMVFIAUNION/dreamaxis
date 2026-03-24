<p align="center">
  <img src="docs/assets/readme/dreamaxis-icon.png" alt="DreamAxis logo" width="112" />
</p>

<h1 align="center">DreamAxis</h1>

<p align="center">
  <strong>Local-first open-source agent execution platform for self-hosted AI workflows.</strong>
</p>

<p align="center">
  DreamAxis turns models, runtimes, skills, and knowledge into reusable local assets instead of a hosted black box.
</p>

<p align="center">
  <img alt="local-first" src="https://img.shields.io/badge/local--first-yes-0f172a">
  <img alt="auth-local-open" src="https://img.shields.io/badge/auth-local__open-default-38bdf8">
  <img alt="runtime-cli-browser-desktop" src="https://img.shields.io/badge/runtime-CLI%20%2B%20Browser%20%2B%20Desktop-67e8f9">
  <img alt="skill-packs" src="https://img.shields.io/badge/skill%20packs-builtin%20%2B%20imported-94a3b8">
  <img alt="knowledge-packs" src="https://img.shields.io/badge/knowledge-packs%20%2B%20uploads-a78bfa">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-22c55e">
</p>

## Why DreamAxis

DreamAxis is built for operators and builders who want:

- **no signup by default** with `AUTH_MODE=local_open`
- **self-hosted provider keys** instead of a central account dependency
- **CLI + Browser + Desktop runtimes** for real execution, not chat alone
- **skill packs** that can be reused, imported, and expanded
- **knowledge packs + uploads** that compound into durable project memory
- a stronger local baseline aligned with modern desktop coding assistants:
  **Git + Node.js + pnpm/npm + Python**

## The core promise

DreamAxis is designed around four simple defaults:

- **local-first** - run on your own machine and infrastructure first
- **no-signup by default** - the main path starts with `AUTH_MODE=local_open`
- **runtime-centric** - use CLI, browser, and desktop execution instead of chat text alone
- **self-hosted assets** - keep provider keys, skills, knowledge, and workspace data under your control

## Verified acceptance status

Latest local acceptance baseline:

- **v0.2 chat-first repo copilot:** `8/8` scenarios passed
- **NVIDIA Build provider validation:** `9/9` scenarios passed
- **grounded verify / troubleshoot loop:** grounded targets, reflection-aware follow-up, failure summaries, stderr highlights, and grounded next-step reasoning are now rendered in chat-first verify / troubleshoot flows
- **Windows host desktop runtime:** inspect, verify, and approval-gated operate flows validated with real `focus_window`, `launch_app`, `press_hotkey`, `type_text`, and `click` actions
- validated across:
  - DreamAxis
  - a Node.js repo
  - a Python repo
- focused on:
  - visible chat modes
  - verify / troubleshoot flows
  - proposal-only repair output
  - runtime-backed evidence and parent/child execution linkage

See:

- [docs/chat-acceptance-report-v0.2.md](./docs/chat-acceptance-report-v0.2.md)
- [docs/chat-acceptance-report-nvidia.md](./docs/chat-acceptance-report-nvidia.md)
- [docs/repo-copilot-runbook.md](./docs/repo-copilot-runbook.md)
- [docs/desktop-host-validation-2026-03-24.md](./docs/desktop-host-validation-2026-03-24.md)

## Screenshots

### Dashboard

![DreamAxis Dashboard](docs/assets/readme/dreamaxis-dashboard.png)

*Operational overview for providers, runtimes, skills, knowledge, and workspace activity.*

### Product surfaces

| Skills | Runtime |
|---|---|
| ![DreamAxis Skills](docs/assets/readme/dreamaxis-skills.png) | ![DreamAxis Runtime](docs/assets/readme/dreamaxis-runtime.png) |
| Skill packs, execution entrypoints, and capability-aware actions. | Runtime hosts, CLI/browser/desktop execution bundles, child executions, and audit-ready trails back to chat turns. |

| Knowledge | Chat |
|---|---|
| ![DreamAxis Knowledge](docs/assets/readme/dreamaxis-knowledge.png) | ![DreamAxis Chat](docs/assets/readme/dreamaxis-chat.png) |
| Builtin packs, uploaded documents, and retrieval-ready assets. | Desktop-first grounded control console with visible targets, approval gates, approved desktop actions, runtime evidence, and proposal-only repo repair guidance. |

See [docs/screenshots.md](./docs/screenshots.md) for the canonical screenshot index and refresh rules.

## What you can do with it

### Run locally

- bootstrap directly into the app with `local_open`
- use Docker for the full stack or run services separately
- validate machine and workspace readiness from `/environment`

### Bring your own model gateway

- configure your own OpenAI-compatible base URL and API key
- sync available models or enter a model manually
- keep provider secrets self-hosted in your own deployment

### Execute via CLI + Browser + Desktop

- run CLI skills against your local workspace
- run Playwright-backed browser skills and capture artifacts
- inspect the Windows desktop surface through the host desktop runtime
- execute approval-gated desktop actions with runtime-backed audit trails
- review runtime hosts, sessions, executions, and outputs in one place
- use chat-first verify / troubleshoot flows with grounded targets, reflection-aware follow-up, and runtime-backed failure summaries instead of black-box answers

## What makes it different

### Local-first by default

- default mode is `AUTH_MODE=local_open`
- no public registration flow is required for a local install
- metadata stays in **your PostgreSQL**
- uploaded knowledge files stay on **your disk**
- provider API keys stay **self-hosted**

### Real execution layer

DreamAxis already includes:

- **CLI Runtime v1**
- **Browser Runtime v1 (Playwright)**
- **Desktop Runtime v1 (Windows host worker)**
- runtime/session/execution visibility in the web console
- chat-first troubleshooting summaries and approval-gated desktop actions backed by runtime evidence, not prose-only diagnosis

### Reusable system assets

- **Builtin skill packs:** `core-cli`, `core-browser-playwright`, `core-research`, `core-docs`, `core-knowledge`, `core-repo`
- **Builtin knowledge packs:** Playwright, Git, Docker, Python, TypeScript, FastAPI, Next.js, DreamAxis architecture
- **OpenAI-compatible provider connections:** user-supplied key, configurable base URL, dynamic model selection

### Desktop AI Assistant Standard v1

DreamAxis treats the local environment as a product surface, not a hidden prerequisite:

- **required:** Git, Node.js, pnpm/npm, Python
- **optional:** Docker, Browser Runtime, Playwright
- **Doctor page:** checks readiness before a skill fails

See [docs/environment-standard.md](./docs/environment-standard.md) and [docs/doctor.md](./docs/doctor.md).

## Quick start

### 1. Install the baseline

Recommended local baseline:

- Git
- Node.js 22+
- pnpm 10+ or npm
- Python 3.12+
- Docker Desktop (recommended)

### 2. Clone and install

```powershell
git clone https://github.com/DREAMVFIAUNION/dreamaxis.git
cd dreamaxis
pnpm install
```

### 3. Create `.env`

```powershell
Copy-Item .env.example .env
```

Recommended minimum:

```env
AUTH_MODE=local_open
ENABLE_BROWSER_RUNTIME=true
JWT_SECRET_KEY=change-me-dreamaxis-development-secret
APP_ENCRYPTION_KEY=change-me-with-a-long-random-secret
```

### 4. Start the stack

```powershell
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

### 5. Open the app

- Web: [http://localhost:3000](http://localhost:3000)
- API health: [http://localhost:8000/health](http://localhost:8000/health)

For the full development setup, non-Docker workflow, and reset instructions, see [docs/development.md](./docs/development.md).

## First-run flow

1. Enter directly with `local_open`
2. Open `/settings/providers`
3. Add an OpenAI-compatible API key
4. Sync models or enter one manually
5. Open `/environment` and confirm baseline readiness
6. Run one CLI skill
7. Run one Browser skill
8. Sync builtin knowledge packs
9. Upload a document
10. Open `/chat/local-demo` and send a knowledge-enabled message
11. Inspect `/runtime` for the execution trail

## Where your data lives

- user / workspace / provider / runtime / skill / knowledge metadata -> PostgreSQL
- provider API keys -> encrypted in `provider_connections`
- uploaded documents -> `KNOWLEDGE_STORAGE_PATH`
- browser auth token -> local browser storage

DreamAxis does **not** require a hosted account system for the default path.

## Core routes

- `/dashboard`
- `/chat/[conversationId]`
- `/skills`
- `/knowledge`
- `/runtime`
- `/environment`
- `/settings/providers`
- `/login` (only for optional `password` mode)

## Read the docs

- [docs/architecture.md](./docs/architecture.md)
- [docs/development.md](./docs/development.md)
- [docs/deployment-modes.md](./docs/deployment-modes.md)
- [docs/browser-runtime.md](./docs/browser-runtime.md)
- [docs/desktop-runtime-v1.md](./docs/desktop-runtime-v1.md)
- [docs/skill-packs.md](./docs/skill-packs.md)
- [docs/knowledge-packs.md](./docs/knowledge-packs.md)
- [docs/backend-api.md](./docs/backend-api.md)
- [docs/skill-requirements.md](./docs/skill-requirements.md)
- [docs/launch/README.md](./docs/launch/README.md)
- [docs/launch/csdn-build-log-tutorial.md](./docs/launch/csdn-build-log-tutorial.md)
- [docs/v0.3-desktop-operator-plan.md](./docs/v0.3-desktop-operator-plan.md)
- [ROADMAP.md](./ROADMAP.md)
- [CHANGELOG.md](./CHANGELOG.md)

## Community

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)
- [SECURITY.md](./SECURITY.md)
- [SUPPORT.md](./SUPPORT.md)

## License

DreamAxis is released under the [MIT License](./LICENSE).



