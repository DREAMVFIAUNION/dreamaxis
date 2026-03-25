# DreamAxis Development Guide

## Local prerequisites

- Git
- Node.js 22+
- pnpm 10+ (or npm)
- Python 3.12+
- Docker Desktop

Optional:

- one OpenAI-compatible API key for local smoke tests

Recommended free / low-cost validation path:

- NVIDIA Build using `docs/nvidia-provider-setup.md`

## Environment

Copy:

```powershell
Copy-Item D:/DreamAxis/dreamaxis/.env.example D:/DreamAxis/dreamaxis/.env
```

Important variables:

- `AUTH_MODE`
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `APP_ENCRYPTION_KEY`
- `RUNTIME_SHARED_TOKEN`
- `KNOWLEDGE_STORAGE_PATH`
- `ENABLE_BROWSER_RUNTIME`

Recommended GitHub/default mode:

```env
AUTH_MODE=local_open
ENABLE_BROWSER_RUNTIME=true
```

Desktop baseline notes:

- DreamAxis now treats `git + node + pnpm/npm + python` as the standard local desktop assistant baseline
- Docker and Browser Runtime are enhancement layers, not hard requirements for every prompt skill
- open `/environment` after boot to confirm machine baseline + workspace readiness before blaming a skill failure
- use `docs/repo-copilot-runbook.md` when validating Chat as a repo copilot against real repositories

## Docker workflow

```powershell
cd D:/DreamAxis/dreamaxis
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

If you are reusing an older local PostgreSQL volume, apply the latest migration before expecting new doctor/runtime fields:

```powershell
cd D:/DreamAxis/dreamaxis/apps/api
alembic upgrade head
```

Services:

- `web` -> 3000
- `api` -> 8000
- `worker` -> 8100
- `browser-worker` -> 8200
- `postgres`
- `redis`

Important:

- the Docker CLI worker can only execute against repositories that are mounted into the container
- the default compose setup mounts the DreamAxis repo as `/workspace`
- if you want repo-copilot CLI probes against other local repos, either mount those paths into the worker container or run the CLI worker directly on the host

### Preferred Windows path for arbitrary local repos

If your API is running in Docker but you want DreamAxis to execute directly against repos like `D:\paperclip` or `D:\some-python-repo`, start a second **host-native** CLI worker:

```powershell
cd D:/DreamAxis/dreamaxis
./scripts/start-host-worker.ps1 -InstallDeps
```

Default host-worker behavior:

- binds on `0.0.0.0:8110`
- registers as `runtime-cli-host-local`
- advertises `http://host.docker.internal:8110` back to the Docker API
- marks itself as `access_mode=host`

Why this matters:

- the Docker worker is best for repos already mounted into `/workspace`
- the host worker is best for arbitrary Windows paths that the container cannot see directly
- DreamAxis now prefers a runtime that can actually access the workspace root path before dispatching CLI execution

## Non-Docker workflow

### API

```powershell
cd D:/DreamAxis/dreamaxis/apps/api
python -m pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### CLI worker

```powershell
cd D:/DreamAxis/dreamaxis/apps/worker
python -m pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

### Host-native CLI worker for arbitrary Windows repos

When the API is in Docker and the repo you want to inspect lives outside the mounted `/workspace` tree, prefer:

```powershell
cd D:/DreamAxis/dreamaxis
./scripts/start-host-worker.ps1 -InstallDeps
```

Useful overrides:

```powershell
./scripts/start-host-worker.ps1 `
  -ApiBaseUrl http://localhost:8000 `
  -PublicUrl http://host.docker.internal:8110 `
  -RuntimeId runtime-cli-host-local `
  -RuntimeName "Host CLI Runtime" `
  -ScopeType machine `
  -ScopeRefId host-local
```

If the API is **not** running in Docker, use a localhost public URL instead:

```powershell
./scripts/start-host-worker.ps1 -PublicUrl http://127.0.0.1:8110
```

### Browser worker

```powershell
cd D:/DreamAxis/dreamaxis/apps/browser-worker
python -m pip install -e .
playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8200
```

### Web

```powershell
cd D:/DreamAxis/dreamaxis
pnpm install
pnpm --filter @dreamaxis/web dev
```

## First-run developer validation

After startup:

1. open the app
2. confirm `local_open` enters without a required login page
3. open `/settings/providers`
4. add a test OpenAI-compatible connection
5. sync models or enter one manually
6. open `/environment`
7. verify missing tools / install guidance / workspace readiness
8. open `/skills`
9. run a CLI skill
10. run a Browser skill
11. open `/knowledge`
12. sync builtin knowledge packs
13. upload one file
14. open `/chat/local-demo`
15. send a knowledge-enabled prompt
16. open `/runtime`
17. verify CLI + Browser + prompt executions are all visible

### NVIDIA validation workflow

Use the scripted path when you want to validate DreamAxis against a real external model gateway without changing repo-tracked secrets:

```powershell
cd D:/DreamAxis/dreamaxis
$env:DREAMAXIS_NVIDIA_API_KEY="your-local-key"
python scripts/run_nvidia_repo_copilot_validation.py
```

Outputs:

- `docs/chat-acceptance-report-nvidia.md`
- provider validation summary
- scenario-based repo-copilot acceptance results

Reference docs:

- `docs/nvidia-provider-setup.md`
- `docs/repo-copilot-runbook.md`
- `docs/notebooklm-evaluation.md`

## Rich text acceptance harness

Use the tracked fixture-driven harness when you need to re-check Markdown, code, math, Mermaid, or operator/runtime explanatory rendering before updating `main` or refreshing README screenshots.

Local route:

```powershell
http://localhost:3000/acceptance/rich-text-v1
```

Tracked evidence:

- fixtures: `docs/acceptance/rich-text-v1/fixtures/`
- screenshots: `docs/acceptance/rich-text-v1/screenshots/`
- report: `docs/acceptance/rich-text-v1/acceptance-report.md`
- visual artifacts output: `artifacts/acceptance/rich-text-v1/`

Local command (with the web app already running):

```powershell
cd D:/DreamAxis/dreamaxis
$env:DREAMAXIS_ACCEPTANCE_BASE_URL="http://127.0.0.1:3000"
pnpm acceptance:rich-text
```

Expected screenshot set:

- `chat-01-streaming-rich.png`
- `chat-02-markdown-basics.png`
- `chat-03-code-highlight.png`
- `chat-04-math-katex-all-syntax.png`
- `chat-05-mermaid-success.png`
- `chat-06-mermaid-fallback-with-src.png`
- `chat-07-html-escaped.png`
- `chat-08-narrow-viewport.png`
- `operator-01-plan-summary-rich.png`
- `operator-02-failure-summary-rich.png`
- `runtime-01-execution-summary-rich.png`
- `runtime-02-approval-summary-rich.png`
- `runtime-03-raw-logs-monospace.png`

Guardrails:

- streaming should stay rich-rendered without breaking on partial Markdown or Mermaid fences
- Mermaid failures must degrade locally with visible source
- raw logs / stderr / JSON payloads must remain plain monospace output
- use fixed fixtures for acceptance evidence instead of ad-hoc live conversations
- CI now mirrors this fixture-driven pass through `.github/workflows/web-acceptance-visual.yml`

## Knowledge indexing behavior

- builtin knowledge packs can sync without embeddings
- retrieval-ready chunks are only created when a valid embedding-capable provider connection is configured
- if embedding creation fails, the product should show a safe operator-facing message instead of raw provider errors

## Validation commands

### Python compile

```powershell
cd D:/DreamAxis/dreamaxis
python -m compileall apps/api/app apps/worker/app apps/browser-worker/app
```

### Frontend production build

```powershell
cd D:/DreamAxis/dreamaxis
pnpm --filter @dreamaxis/web build
```

### Docker status

```powershell
docker compose -f D:/DreamAxis/dreamaxis/infrastructure/docker/docker-compose.yml ps
```

## Resetting the local demo state

When you want to clean out local demo history without rebuilding the whole stack:

```powershell
cd D:/DreamAxis/dreamaxis
./scripts/reset-local-demo.ps1 -Yes
```

Dry run:

```powershell
cd D:/DreamAxis/dreamaxis
python scripts/reset-local-demo.py --dry-run
```

Default reset behavior:

- removes conversations/messages in the seeded workspace
- clears runtime sessions and runtime executions
- removes uploaded knowledge docs and their stored files
- removes imported/non-builtin packs in the seeded workspace
- preserves provider connections unless `--reset-provider-connections` is passed
- preserves runtime hosts unless `--reset-runtime-hosts` is passed
- re-seeds demo data and re-syncs builtin packs

## Seeded local objects

On API startup DreamAxis seeds:

- local owner user
- default workspace: `workspace-main`
- default conversation: `local-demo`
- default provider shell connection
- builtin skill packs
- builtin knowledge packs
- agent role registry

## Current development boundaries

- no public signup / email verification
- no central marketplace dependency
- no full multi-agent workflow orchestration yet
- no advanced RBAC yet
- no native Anthropic / Gemini protocol adapters yet
