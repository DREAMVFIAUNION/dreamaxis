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

## Next major track: v0.2.x operator usefulness

Focus:

- better builtin skill coverage
- stronger browser actions and artifacts
- richer knowledge ingestion
- improved provider/model UX
- more polished runtime observability

Candidate work:

- browser extract/selector ergonomics
- repo and docs skill pack expansion
- better retry/error surfaces in chat and runtime
- more importable pack examples
- improved runtime artifact previews

## v0.3.x execution platform maturity

Focus:

- stronger execution safety
- more reusable knowledge and pack tooling
- deeper workspace-scoped workflows

Candidate work:

- git repo knowledge ingestion
- web capture knowledge ingestion
- stronger policy controls for runtime execution
- pack import/version management improvements
- richer execution audit trails

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
