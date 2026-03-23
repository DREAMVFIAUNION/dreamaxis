# Contributing to DreamAxis

Thanks for helping build DreamAxis.

DreamAxis is a **local-first, self-hosted, open-source runtime + skill + knowledge platform**. The project defaults matter:

- `AUTH_MODE=local_open` stays the default unless there is an explicit product decision to change it
- no hosted account dependency
- provider keys stay self-hosted
- builtin skill packs, knowledge packs, and runtimes should keep working in a fresh local setup

## What to work on

Good first contribution areas:

- runtime stability and observability
- skill pack improvements
- builtin knowledge quality
- browser runtime coverage
- docs, onboarding, and local DX
- UI polish that preserves the current DreamAxis command-center direction

## Local setup

### Docker

```powershell
cd D:/DreamAxis/dreamaxis
Copy-Item .env.example .env
docker compose -f infrastructure/docker/docker-compose.yml up --build
```

### Non-Docker

See:

- [README.md](./README.md)
- [docs/development.md](./docs/development.md)

## Default validation path

Before opening a PR, run the checks relevant to your change.

### Backend sanity check

```powershell
cd D:/DreamAxis/dreamaxis
python -m compileall apps/api/app apps/worker/app apps/browser-worker/app
```

### Frontend production build

```powershell
cd D:/DreamAxis/dreamaxis
pnpm --filter @dreamaxis/web build
```

### Local runtime smoke path

After the stack starts:

1. enter the app without signup in `local_open`
2. configure a provider connection in `/settings/providers`
3. run one CLI skill
4. run one Browser skill
5. sync builtin knowledge packs
6. upload one document
7. send one chat message
8. confirm `/runtime` shows the execution trail

## Contribution guidelines

### 1. Keep the project local-first

Do not introduce:

- forced signup for the default path
- dependency on a hosted marketplace
- server-side storage of user secrets outside the local deployment

### 2. Keep changes scoped

Prefer small PRs with one clear theme:

- one runtime feature
- one pack improvement
- one API surface expansion
- one documentation pass

### 3. Update docs with behavior changes

If you change any of these, update docs in the same PR:

- setup flow
- environment variables
- API routes
- runtime behavior
- pack manifest shape
- auth behavior

### 4. Be explicit about safety boundaries

If your change touches CLI or Browser execution, document:

- allowed scope
- deny/guard behavior
- artifact behavior
- failure handling

### 5. Preserve seeded local usability

A fresh clone should still be able to:

- boot in `local_open`
- create a local operator session
- see builtin packs
- run the primary demo flows

## Pull request expectations

Please include:

- what changed
- why it changed
- how you tested it
- screenshots for UI changes
- any follow-up work that is intentionally deferred

Use the PR template in `.github/PULL_REQUEST_TEMPLATE.md`.

## Security issues

Do **not** post exploit details in a public bug report first.

Please follow [SECURITY.md](./SECURITY.md).

## Community expectations

By participating, you agree to follow [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
