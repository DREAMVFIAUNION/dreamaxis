# Changelog

All notable changes to DreamAxis will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- rich text v1 rendering foundation for `@dreamaxis/web`, including:
  - shared Markdown/GFM renderer for chat, operator, and runtime explanatory text
  - syntax-highlighted code blocks with copy affordances and long-block collapse
  - KaTeX math rendering for `$...$`, `\(...\)`, `$$...$$`, and `\[...\]` fixture coverage
  - client-side Mermaid rendering with local failure isolation and visible source fallback
- deterministic rich-text acceptance harness at `/acceptance/rich-text-v1` with fixed fixtures and 13 tracked screenshot artifacts
- rich-text acceptance evidence docs under `docs/acceptance/rich-text-v1/`

### Changed

- streaming chat responses now use tolerant rich rendering instead of plain `<pre>` output, reducing completion-state layout jumps
- operator and runtime explanatory summaries now share the same safe rich-content renderer while raw logs, stderr, and JSON payloads remain monospace
- README and screenshot index now reference the tracked rich-text acceptance screenshot set directly

### Validated

- `pnpm --dir D:\DreamAxis\dreamaxis --filter @dreamaxis/web build`
- fixed-fixture rich-text acceptance coverage across chat, operator, runtime, Mermaid fallback, HTML escaping, and narrow viewport rendering

### Planned

- v0.3 desktop-operator roadmap docs and motion-console direction
- desktop-first product positioning and dual-lane repo/desktop planning

## [0.3.0-alpha.2] - 2026-03-25

### Added

- OperatorPlan alpha.2 workflow surface:
  - `POST /api/v1/operator-plans`
  - `GET /api/v1/operator-plans`
  - `GET /api/v1/operator-plans/{id}`
  - `POST /api/v1/operator-plans/{id}/approve`
  - `POST /api/v1/operator-plans/{id}/deny`
  - `POST /api/v1/operator-plans/{id}/resume`
- deterministic desktop grounding extraction with stable `DesktopContextSnapshot` and `DesktopTargetResolverResult` outputs
- grounded multi-step operator executor with:
  - ordered inspect / verify / operate / proposal steps
  - approval checkpoints for gated desktop actions
  - bounded helper reflection (`MAX_HELPER_REFLECTIONS = 1`)
  - bounded retry (`MAX_STEP_RETRIES = 1`)
  - resume support from paused / denied / pending approval states
  - plan-level approval history aggregation
- reusable alpha.2 acceptance runner:
  - `scripts/run_alpha2_acceptance.py`
- release evidence docs:
  - `docs/acceptance-report-alpha2.md`
  - `docs/github-release-v0.3.0-alpha.2.md`

### Changed

- `/chat` now reads as an operator console with:
  - active-step emphasis
  - approval banner prominence
  - operator strip status
  - direct linkage back to operator plans
- `/runtime` now emphasizes audit-first operator lineage, verification evidence, and compressed raw output over generic log streaming
- `/operator` now acts as a management surface for approval queue, active runs, plan inspection, and template-driven starts
- operator-plan creation now eagerly loads the conversation provider connection to avoid async lazy-load failures during plan bootstrap
- README and canonical screenshots now reflect the alpha.2 operator queue, approval-gated chat flow, and runtime audit plane

### Validated

- `python -m compileall apps/api/app apps/desktop-worker/app`
- `pnpm --filter @dreamaxis/web build`
- alpha.2 acceptance baseline: `9/9` scenarios passed across 6 scenario families
- validated operator scenarios:
  - inspect desktop
  - verify browser
  - operate with approval
  - browser + terminal + VS Code triad
- validated repo scenarios:
  - failure + reflection narrowing
  - understand repo
  - inspect repo
  - verify repo
  - propose fix
- proposal-only repo/code behavior remained intact during alpha.2 acceptance
- acceptance evidence recorded in `docs/acceptance-report-alpha2.md`

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
