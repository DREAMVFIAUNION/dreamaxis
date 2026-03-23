# DreamAxis Development Guide

## Local prerequisites

- Git
- Node.js 22+
- pnpm 10+ (or npm)
- Python 3.12+
- Docker Desktop

Optional:

- one OpenAI-compatible API key for local smoke tests

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
