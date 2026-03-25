# DreamAxis Screenshot Index

## Canonical README screenshots

The GitHub README uses tracked documentation assets from:

- `docs/assets/readme/dreamaxis-dashboard.png`
- `docs/assets/readme/dreamaxis-chat.png`
- `docs/assets/readme/dreamaxis-skills.png`
- `docs/assets/readme/dreamaxis-operator.png`
- `docs/assets/readme/dreamaxis-knowledge.png`
- `docs/assets/readme/dreamaxis-runtime.png`
- `docs/assets/readme/dreamaxis-icon.png`

These are the stable, repo-tracked files that should remain safe for:

- GitHub README rendering
- long-lived documentation
- future release note references

README also now references the rich-text acceptance screenshot set directly from:

- `docs/acceptance/rich-text-v1/screenshots/chat-02-markdown-basics.png`
- `docs/acceptance/rich-text-v1/screenshots/chat-03-code-highlight.png`
- `docs/acceptance/rich-text-v1/screenshots/chat-04-math-katex-all-syntax.png`
- `docs/acceptance/rich-text-v1/screenshots/chat-05-mermaid-success.png`
- `docs/acceptance/rich-text-v1/screenshots/chat-06-mermaid-fallback-with-src.png`
- `docs/acceptance/rich-text-v1/screenshots/operator-01-plan-summary-rich.png`

Recommended README order:

1. `dreamaxis-dashboard.png`
2. `dreamaxis-skills.png`
3. `dreamaxis-operator.png`
4. `dreamaxis-runtime.png`
5. `dreamaxis-knowledge.png`
6. `dreamaxis-chat.png`

## Acceptance source screenshots

Fresh UI acceptance captures are still generated locally in:

- `artifacts/acceptance/dreamaxis-dashboard.png`
- `artifacts/acceptance/dreamaxis-chat.png`
- `artifacts/acceptance/dreamaxis-skills.png`
- `artifacts/acceptance/dreamaxis-knowledge.png`
- `artifacts/acceptance/dreamaxis-runtime.png`
- `artifacts/acceptance/alpha2-chat-approval.png`
- `artifacts/acceptance/alpha2-operator-queue.png`
- `artifacts/acceptance/alpha2-runtime-audit.png`

Because `artifacts/` stays gitignored, those files are **not** the source used by the public README.

These acceptance exports are the preferred source for:

- GitHub release assets
- social launch visuals
- community post attachments

## Current mapping

- `dreamaxis-dashboard.png` - control-center overview
- `dreamaxis-chat.png` - conversation lane / stream UI
- `dreamaxis-skills.png` - skill pack and execution surface
- `dreamaxis-operator.png` - operator approval queue, active runs, and plan control surface
- `dreamaxis-knowledge.png` - documents, packs, and sources view
- `dreamaxis-runtime.png` - runtime/session/execution console

## Refresh workflow

When the UI changes:

1. regenerate acceptance screenshots in `artifacts/acceptance/`
2. choose the canonical images for README usage
3. copy those images into `docs/assets/readme/`
4. keep `README.md` and this file pointing only at `docs/assets/readme/`
5. rerun the fixture-driven rich-text visual gate so `/acceptance/rich-text-v1` stays aligned with tracked baselines

## Refresh guidance

Try to keep screenshots:

- taken from the same viewport size
- based on seeded demo data
- free of raw secrets or provider error payloads
- visually aligned with the current README narrative

Latest refresh notes:

- `2026-03-25`: README now includes a dedicated "Rich Text v1 acceptance samples" section that references deterministic screenshot artifacts from `docs/acceptance/rich-text-v1/screenshots/`
- `2026-03-25`: rich-text README references now cover Markdown basics, code highlighting, KaTeX, Mermaid success, Mermaid fallback with source, and operator explanatory text rendering
- `2026-03-25`: `.github/workflows/web-acceptance-visual.yml` now rechecks the rich-text fixture screenshots in CI and uploads current/diff artifacts for review

- `2026-03-25`: README canonical `docs/assets/readme/dreamaxis-operator.png` added from `artifacts/acceptance/alpha2-operator-queue.png` to represent the alpha.2 approval queue and active-run management surface
- `2026-03-25`: README canonical `docs/assets/readme/dreamaxis-chat.png` refreshed from `artifacts/acceptance/alpha2-chat-approval.png` and now centers the public chat surface on active-step focus, approval prominence, and operator-linked runtime evidence
- `2026-03-25`: README canonical `docs/assets/readme/dreamaxis-runtime.png` refreshed from `artifacts/acceptance/alpha2-runtime-audit.png` and now centers the public runtime surface on audit-plane lineage, artifacts, and verification summaries
- `2026-03-25`: `artifacts/acceptance/dreamaxis-chat.png` refreshed to the desktop-first operator-console view with visible grounded target selection, approval state, runtime linkage, and approved desktop action evidence
- `2026-03-25`: README canonical `docs/assets/readme/dreamaxis-chat.png` refreshed from the latest desktop host validation run and now anchors the public chat surface on grounded desktop control instead of repo-only troubleshooting
- `2026-03-25`: `artifacts/acceptance/dreamaxis-runtime.png` refreshed to a desktop execution-detail view with selected execution, parent linkage, action timeline, and runtime artifacts
- `2026-03-25`: README canonical `docs/assets/readme/dreamaxis-runtime.png` refreshed from the latest approved desktop action run and now anchors the public runtime surface on desktop audit lineage instead of the older broad control-plane list
- `2026-03-24`: `artifacts/acceptance/dreamaxis-chat.png` refreshed as the v0.2 acceptance composite (verify / troubleshoot failure summary + propose-fix proposal-only lane)
- `2026-03-24`: README canonical `docs/assets/readme/dreamaxis-chat.png` refreshed to the grounded verify / troubleshoot operator-console view with visible target selection, reflection, failure summary, and runtime linkage from the latest `8/8 PASS` acceptance run
- `2026-03-24`: README canonical `docs/assets/readme/dreamaxis-runtime.png` refreshed from the latest runtime control-plane capture showing bundle / child execution linkage for grounded chat turns
- `2026-03-24`: `artifacts/acceptance/dreamaxis-runtime.png` retained as the preferred runtime acceptance capture after the v0.2 UI polish pass
