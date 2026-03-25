# Changelog

All notable changes to DreamAxis will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Planned

- v0.3 desktop-operator roadmap docs and motion-console direction
- desktop-first product positioning and dual-lane repo/desktop planning

## [0.2.0-preview] - 2026-03-25

### Added

- chat-first repo copilot execution bundle with grounded target, reflection-aware follow-up, failure summary, stderr highlights, and grounded next-step reasoning
- Windows host Desktop Runtime v1 for real local desktop inspection and approval-gated operation
- first approved desktop actions validated end to end:
  - `focus_window`
  - `launch_app`
  - `press_hotkey`
  - `type_text`
  - `click`
- desktop host validation docs:
  - `docs/desktop-runtime-v1.md`
  - `docs/desktop-host-validation-2026-03-24.md`
- desktop-first operator roadmap docs:
  - `docs/v0.3-desktop-operator-plan.md`
  - `docs/vnext-desktop-operator-first-plan.md`

### Changed

- README repositioned from repo-copilot-only messaging toward a desktop-first grounded control narrative
- canonical chat screenshot refreshed to the approved desktop action operator-console view
- canonical runtime screenshot refreshed to the desktop execution-detail audit view
- screenshot index updated to reflect the current public GitHub assets
- runtime control plane now surfaces desktop execution detail, parent linkage, action timeline, and artifact visibility more clearly

### Validated

- `python -m compileall apps/api/app apps/desktop-worker/app`
- `pnpm --filter @dreamaxis/web build`
- host desktop worker health at `http://127.0.0.1:8300/health`
- real approved desktop action scenario:
  - `Focus Chrome, press ctrl+l, and type "https://example.com".`

### Added

- GitHub community scaffolding:
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
  - `SUPPORT.md`
- GitHub issue and pull request templates
- GitHub Actions CI workflow for:
  - Python compile checks
  - web build
  - Docker smoke validation
- local demo reset scripts:
  - `scripts/reset-local-demo.py`
  - `scripts/reset-local-demo.ps1`
- release support docs:
  - `docs/release-checklist.md`
  - `docs/github-release-template.md`
  - `docs/screenshots.md`

### Changed

- README upgraded for public GitHub release readiness
- architecture doc refreshed with a mermaid system overview

## [0.1.0] - 2026-03-23

### Added

- local-first DreamAxis monorepo foundation
- Next.js web control center
- FastAPI backend API
- PostgreSQL + Redis + Docker Compose local stack
- `local_open` auth mode with bootstrap session flow
- optional `password` auth mode
- OpenAI-compatible provider connection management
- dynamic model selection flow
- knowledge uploads and builtin knowledge packs
- skill packs with prompt / CLI / browser modes
- CLI Runtime v1
- Browser Runtime v1 (Playwright)
- runtime/session/execution visibility in the UI
- agent role registry foundation
