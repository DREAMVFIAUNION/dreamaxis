# DreamAxis Roadmap

This roadmap reflects the current open-source direction:

- **local-first**
- **no-signup by default**
- **self-hosted**
- **runtime + skill + knowledge platform**
- **desktop-first operator direction**

## Current baseline: v0.1.x foundation

Already in place:

- `local_open` default auth
- optional `password` mode
- OpenAI-compatible provider connections
- CLI Runtime v1
- Browser Runtime v1 (Playwright)
- builtin skill packs
- builtin knowledge packs
- runtime/session/execution visibility
- GitHub-ready community scaffolding

## Current expansion baseline: v0.2.x repo copilot + desktop foundations

Already validated on top of the v0.1 foundation:

- chat-first repo copilot flows for understand / inspect / verify / propose-fix
- grounded verify / troubleshoot summaries with evidence-first chat output
- Browser Runtime artifacts wired into chat and runtime
- Windows host Desktop Runtime v1
- approval-gated desktop actions:
  - `focus_window`
  - `launch_app`
  - `press_hotkey`
  - `type_text`
  - `click`
- README and canonical screenshots updated to the desktop-first operator narrative

Reference docs:

- `docs/chat-acceptance-report-v0.2.md`
- `docs/desktop-host-validation-2026-03-24.md`
- `docs/desktop-runtime-v1.md`

## Next major track: v0.3.x desktop operator alpha

Focus:

- make DreamAxis a **desktop-first local operator**
- keep `/chat` as the primary entrypoint with **gated actions**
- keep repo copilot as a specialized professional lane
- deepen approval-backed Windows control and runtime audit
- add motion/compression so live execution reads like an operator console, not a raw log wall

Candidate work:

- desktop grounding v1: windows, processes, focus state, screenshot / OCR, desktop targets
- approval contract hardening for state-changing actions
- runtime detail polish for desktop execution lineage and artifacts
- motion UI: execution strip, compressed cards, approval prominence, active-step pinning
- browser + terminal + VS Code as the first coherent desktop app surface
- repo/desktop dual-lane chat routing

Detailed plan:

- `docs/vnext-desktop-operator-first-plan.md`
- `docs/v0.3-desktop-operator-plan.md`

## v0.4.x agent-role enablement

Focus:

- make the role registry materially useful without overcomplicating the product

Candidate work:

- role-to-pack presets in UI
- role-specific execution entrypoints
- role-specific default knowledge scopes
- role-aware skill filtering

## Deliberately not prioritized right now

These are intentionally not first:

- public signup SaaS motion
- central hosted marketplace dependency
- forced cloud control plane
- native multi-vendor protocol sprawl before OpenAI-compatible flow is solid
- overbuilt orchestration DAGs before runtime value is proven

## Success criteria

DreamAxis wins if a new GitHub user can:

1. clone the repo
2. run Docker Compose
3. enter without signup
4. add an API key
5. run a CLI skill
6. run a Browser skill
7. upload/sync knowledge
8. inspect the full runtime trail
