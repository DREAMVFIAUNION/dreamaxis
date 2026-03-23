# DreamAxis Screenshot Index

## Canonical README screenshots

The GitHub README uses tracked documentation assets from:

- `docs/assets/readme/dreamaxis-dashboard.png`
- `docs/assets/readme/dreamaxis-chat.png`
- `docs/assets/readme/dreamaxis-skills.png`
- `docs/assets/readme/dreamaxis-knowledge.png`
- `docs/assets/readme/dreamaxis-runtime.png`
- `docs/assets/readme/dreamaxis-icon.png`

These are the stable, repo-tracked files that should remain safe for:

- GitHub README rendering
- long-lived documentation
- future release note references

Recommended README order:

1. `dreamaxis-dashboard.png`
2. `dreamaxis-skills.png`
3. `dreamaxis-runtime.png`
4. `dreamaxis-knowledge.png`
5. `dreamaxis-chat.png`

## Acceptance source screenshots

Fresh UI acceptance captures are still generated locally in:

- `artifacts/acceptance/dreamaxis-dashboard.png`
- `artifacts/acceptance/dreamaxis-chat.png`
- `artifacts/acceptance/dreamaxis-skills.png`
- `artifacts/acceptance/dreamaxis-knowledge.png`
- `artifacts/acceptance/dreamaxis-runtime.png`

Because `artifacts/` stays gitignored, those files are **not** the source used by the public README.

These acceptance exports are the preferred source for:

- GitHub release assets
- social launch visuals
- community post attachments

## Current mapping

- `dreamaxis-dashboard.png` - control-center overview
- `dreamaxis-chat.png` - conversation lane / stream UI
- `dreamaxis-skills.png` - skill pack and execution surface
- `dreamaxis-knowledge.png` - documents, packs, and sources view
- `dreamaxis-runtime.png` - runtime/session/execution console

## Refresh workflow

When the UI changes:

1. regenerate acceptance screenshots in `artifacts/acceptance/`
2. choose the canonical images for README usage
3. copy those images into `docs/assets/readme/`
4. keep `README.md` and this file pointing only at `docs/assets/readme/`

## Refresh guidance

Try to keep screenshots:

- taken from the same viewport size
- based on seeded demo data
- free of raw secrets or provider error payloads
- visually aligned with the current README narrative

Latest refresh notes:

- `2026-03-23`: `dreamaxis-chat.png` refreshed from the v0.2 verify lane acceptance pass
- `2026-03-23`: `dreamaxis-runtime.png` refreshed from the v0.2 runtime control plane after bundle-aware acceptance
