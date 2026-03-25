# DreamAxis v0.3.0-alpha.2

DreamAxis `v0.3.0-alpha.2` turns the v0.3 operator direction into a validated product slice:

- **OperatorPlan-backed execution**
- **approval-gated desktop operate flows**
- **deterministic desktop grounding**
- **chat / operator / runtime split by responsibility**
- **proposal-only repo lane preserved**

This release keeps the trust model unchanged:

- **local-first**
- **Windows-first**
- **runtime-backed audit**
- **gated actions**
- **proposal-only for repo/code writes**

## Highlights

### OperatorPlan workflow is now real

Alpha.2 adds a stable operator workflow layer with:

- `POST /api/v1/operator-plans`
- `GET /api/v1/operator-plans`
- `GET /api/v1/operator-plans/{id}`
- `POST /api/v1/operator-plans/{id}/approve`
- `POST /api/v1/operator-plans/{id}/deny`
- `POST /api/v1/operator-plans/{id}/resume`

This gives DreamAxis a first-class plan object for multi-step operator work instead of treating every action as an isolated turn.

### Chat is now the live operator console

`/chat` now emphasizes:

- current plan linkage
- active-step visibility
- approval prominence
- execution strip status
- runtime-backed evidence

The goal is that the user can tell what is active, what is waiting, and what failed without reading a raw log stream.

### `/operator` is now the management surface

`/operator` now acts as the approval and plan-management page, including:

- approval queue
- active runs
- all plans
- plan detail inspection
- template-driven starts

### `/runtime` is now the audit plane

`/runtime` now reads as an audit surface rather than a generic runtime log view, with stronger emphasis on:

- execution lineage
- artifacts
- verification summaries
- failure visibility
- parent/child linkage

### Deterministic desktop grounding was extracted

Desktop grounding was split into a dedicated deterministic layer so the executor can consume stable results instead of inlined branching logic.

Stable shared outputs now include:

- `DesktopContextSnapshot`
- `DesktopTargetResolverResult`

### Operator execution is bounded and reviewable

The alpha.2 executor now supports:

- ordered inspect / verify / operate / proposal steps
- approval checkpoints for gated actions
- bounded reflection
- bounded retry
- resume after pause / denial / approval
- plan-level approval history aggregation

## Acceptance summary

Acceptance evidence is recorded in:

- `docs/acceptance-report-alpha2.md`

Recorded result:

- `9/9` scenarios passed
- `0 partial`
- `0 fail`
- `0 blocked`

Scenario families covered:

1. inspect desktop
2. verify browser
3. operate with approval
4. browser + terminal + VS Code triad
5. failure + reflection narrowing
6. repo lane non-regression:
   - `understand_repo`
   - `inspect_repo`
   - `verify_repo`
   - `propose_fix`

## Public product shape after alpha.2

DreamAxis is now best understood as:

**a local-first operator workflow platform with approval-gated desktop action lanes and a proposal-only repo copilot lane**

Current visible surfaces:

- `/chat` for live operation
- `/operator` for approval and plan management
- `/runtime` for audit and lineage

## What this release still does not do

Alpha.2 is intentionally **not**:

- hidden autonomous computer use
- unrestricted system control
- silent file editing
- WebSocket/SSE push
- macOS/Linux parity
- multi-agent swarm UX

## Recommended links for the release

- `README.md`
- `docs/acceptance-report-alpha2.md`
- `docs/acceptance/rich-text-v1/acceptance-report.md`
- `docs/desktop-runtime-v1.md`
- `docs/backend-api.md`
- `CHANGELOG.md`

## Post-release UI evidence follow-up

After the alpha.2 release evidence was finalized, the web surface also gained a tracked rich-text acceptance pack that now serves as the canonical proof for final-message Markdown rendering, KaTeX, Mermaid fallback, and operator/runtime explanatory text formatting.

Use these assets when refreshing public docs or validating that README screenshots still match the current UI:

- route: `/acceptance/rich-text-v1`
- report: `docs/acceptance/rich-text-v1/acceptance-report.md`
- screenshots: `docs/acceptance/rich-text-v1/screenshots/`
