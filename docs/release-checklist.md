# DreamAxis GitHub Release Checklist

Use this checklist before publishing or refreshing the public GitHub repository.

## Product/defaults

- [ ] `AUTH_MODE=local_open` remains the default
- [ ] no public signup is required for the default local path
- [ ] provider keys remain self-hosted
- [ ] builtin skill packs sync on a fresh instance
- [ ] builtin knowledge packs sync on a fresh instance
- [ ] CLI Runtime works
- [ ] Browser Runtime works

## Repository hygiene

- [ ] `README.md` reflects the current product direction
- [ ] `CONTRIBUTING.md` exists and is current
- [ ] `CODE_OF_CONDUCT.md` exists
- [ ] `SECURITY.md` exists
- [ ] `SUPPORT.md` exists
- [ ] issue templates exist
- [ ] PR template exists
- [ ] `LICENSE` is present and intentional

## Docs

- [ ] setup steps are accurate
- [ ] environment variables are documented
- [ ] auth modes are documented
- [ ] runtime docs are current
- [ ] skill pack docs are current
- [ ] knowledge pack docs are current
- [ ] reset/demo cleanup flow is documented

## Validation

- [ ] `python -m compileall apps/api/app apps/worker/app apps/browser-worker/app`
- [ ] `pnpm --filter @dreamaxis/web build`
- [ ] `docker compose -f infrastructure/docker/docker-compose.yml up --build`
- [ ] `/dashboard` loads
- [ ] `/skills` loads and can run a CLI skill
- [ ] `/skills` loads and can run a Browser skill
- [ ] `/knowledge` can sync builtin packs
- [ ] `/chat/local-demo` streams successfully
- [ ] `/runtime` shows executions and artifacts

## Assets

- [ ] logo/favicon assets are committed
- [ ] acceptance screenshots are up to date
- [ ] sample screenshots match the current UI

## Optional polish

- [ ] tag a release
- [ ] attach screenshots to the release notes
- [ ] publish a short “first-run” walkthrough
