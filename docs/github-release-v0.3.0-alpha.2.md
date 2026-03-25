# DreamAxis v0.3.0-alpha.2

DreamAxis `v0.3.0-alpha.2` is the first release where the product reads clearly as a **local-first operator workflow platform** instead of a generic chat shell.

This release locks in the new public shape:

- **OperatorPlan-backed execution** for multi-step work
- **approval-gated desktop action lanes** with resume support
- **runtime-backed audit** across chat, operator, and runtime
- **proposal-only repo/code repair lanes**
- **rich final outputs** for Markdown, code, math, and Mermaid

The trust model remains unchanged:

- **local-first**
- **Windows-first**
- **gated actions**
- **runtime-backed evidence**
- **proposal-only for repo/code writes**

## Highlights

### OperatorPlan is now the execution backbone

Alpha.2 introduces a first-class operator workflow object for multi-step work:

- `POST /api/v1/operator-plans`
- `GET /api/v1/operator-plans`
- `GET /api/v1/operator-plans/{id}`
- `POST /api/v1/operator-plans/{id}/approve`
- `POST /api/v1/operator-plans/{id}/deny`
- `POST /api/v1/operator-plans/{id}/resume`

This moves DreamAxis away from isolated one-off turns and toward explicit plan state, approvals, resume, and auditability.

### `/chat` is now the live operator console

`/chat` now centers on live execution rather than plain conversation:

- current plan linkage
- active-step visibility
- approval prominence
- execution strip status
- runtime-backed evidence
- rich final-message rendering

The result is a surface where operators can tell what is active, what is blocked, what failed, and what evidence was produced without reading raw logs first.

### `/operator` is now the management surface

`/operator` is now the control plane for operator work:

- approval queue
- active runs
- all plans
- plan detail inspection
- template-driven starts

### `/runtime` is now the audit plane

`/runtime` now reads as an audit and lineage surface, with emphasis on:

- execution lineage
- artifacts
- verification summaries
- failure visibility
- parent/child linkage
- raw logs preserved as monospace evidence

### Desktop execution stays bounded and reviewable

The alpha.2 executor now supports:

- ordered inspect / verify / operate / proposal steps
- approval checkpoints for gated desktop actions
- bounded reflection
- bounded retry
- resume after pause / denial / approval
- plan-level approval history aggregation

### Rich text v1 now upgrades final outputs

The web surface now includes a shared rich renderer for explanatory text across chat, operator, and runtime:

- Markdown + GFM tables
- syntax-highlighted code blocks
- KaTeX math rendering
- Mermaid diagram rendering
- local Mermaid failure fallback with visible source

This improves final-message readability without changing backend message schemas or weakening HTML safety.

## Acceptance summary

### Operator workflow acceptance

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

### Rich text acceptance

Rich text acceptance evidence is recorded in:

- `docs/acceptance/rich-text-v1/acceptance-report.md`

Recorded result:

- fixed-fixture screenshot acceptance completed
- `13` tracked screenshots captured
- coverage across chat, operator, runtime, Mermaid fallback, HTML escaping, and narrow viewport rendering

Tracked screenshot set:

- `chat-01-streaming-rich.png`
- `chat-02-markdown-basics.png`
- `chat-03-code-highlight.png`
- `chat-04-math-katex-all-syntax.png`
- `chat-05-mermaid-success.png`
- `chat-06-mermaid-fallback-with-src.png`
- `chat-07-html-escaped.png`
- `chat-08-narrow-viewport.png`
- `operator-01-plan-summary-rich.png`
- `operator-02-failure-summary-rich.png`
- `runtime-01-execution-summary-rich.png`
- `runtime-02-approval-summary-rich.png`
- `runtime-03-raw-logs-monospace.png`

## Public product shape after alpha.2

DreamAxis is now best understood as:

**a local-first operator workflow platform with approval-gated desktop action lanes, proposal-only repo/code repair, and rich final outputs backed by runtime evidence**

Current visible surfaces:

- `/chat` = live operator console
- `/operator` = approvals, queues, templates, and plan management
- `/runtime` = audit, lineage, artifacts, and execution detail

## What this release still does not do

Alpha.2 is intentionally **not**:

- hidden autonomous computer use
- unrestricted system control
- silent file editing
- WebSocket/SSE push
- macOS/Linux parity
- multi-agent swarm UX
- WYSIWYG rich-text editing
- raw HTML rendering in messages

## Recommended links for the release

- `README.md`
- `docs/acceptance-report-alpha2.md`
- `docs/acceptance/rich-text-v1/acceptance-report.md`
- `docs/desktop-runtime-v1.md`
- `docs/backend-api.md`
- `CHANGELOG.md`
