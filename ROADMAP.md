# DreamAxis Roadmap

This roadmap reflects the current open-source direction:

- **local-first**
- **no-signup by default**
- **self-hosted**
- **runtime + skill + knowledge platform**

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

## Next major track: v0.2.x repo copilot usefulness

Focus:

- chat as a true repo copilot entrypoint
- safe chat-to-runtime orchestration
- scenario-based validation against real repositories
- clearer execution evidence in chat and runtime
- stronger browser actions and artifacts
- repo-aware verification and troubleshooting depth

Candidate work:

- repo onboarding / readiness / trace / verification / troubleshooting runbooks
- better retry and fallback behavior in chat
- repo and docs skill pack expansion
- browser extract and selector ergonomics
- improved runtime artifact previews
- package-manager-aware verify routing
- stronger failure summarization and proposal-only repair plans

Detailed plan:

- `docs/v0.2-next-round-plan.md`

## v0.3.x desktop operator alpha (Windows-first)

Focus:

- move from repo-copilot-only positioning toward a **local-first desktop operator**
- keep `/chat` as the primary entrypoint with **gated actions**
- make **Windows app control first** the initial desktop lane
- preserve runtime-backed audit trails instead of black-box autonomy
- keep repo copilot as a high-value professional lane inside the wider product

Candidate work:

- desktop grounding v1: windows, processes, focus state, screenshot / OCR, desktop targets
- desktop runtime host v1 for Windows: list windows, focus allowed apps, capture screen, OCR, click, type, hotkeys
- approval contract for state-changing desktop actions
- desktop execution lineage in `/runtime`
- Windows operator scenarios for inspect / verify / operate flows

Detailed plan:

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
