# DreamAxis v0.2.0-preview

DreamAxis has moved beyond the initial local-first foundation and now behaves much more like an **operator-grade desktop AI control plane**.

This preview release keeps the trust model intact:

- **local-first**
- **no-signup by default**
- **runtime-backed audit**
- **gated actions**
- **proposal-only for code and file changes**

## Highlights

### Desktop operator lane is now real

DreamAxis now includes a real **Windows host Desktop Runtime v1** instead of only repo and browser lanes.

Validated desktop actions:

- `focus_window`
- `launch_app`
- `press_hotkey`
- `type_text`
- `click`

These actions are not black-box autonomy. They run behind an approval contract and leave a runtime-backed audit trail.

### Chat is now execution-first

`/chat` now behaves like an operator console instead of a generic AI chat page.

The current turn can surface:

- grounded target
- approval state
- runtime execution bundle
- evidence items
- desktop action artifacts
- recommended next step

Repo-copilot verify / troubleshoot flows also now include:

- reflection-aware follow-up
- failure summaries
- stderr highlights
- grounded next-step reasoning

### Runtime is a real audit surface

`/runtime` now supports a clearer execution-detail view for desktop actions, including:

- selected execution summary
- parent execution linkage
- session lineage
- execution timeline
- runtime artifacts
- source conversation jump-back

## What shipped in this preview

### Core additions

- Windows host Desktop Runtime v1
- desktop action approval path
- desktop-aware runtime detail view
- grounded desktop action summaries in chat
- refreshed public screenshots and README positioning

### Validation passed

- Python compile checks for API + desktop worker
- web production build
- host desktop worker health validation
- real approved desktop action scenario against Chrome

## Current product shape

DreamAxis is now best understood as:

**a local-first desktop operator with a specialized repo-copilot lane**

Current lanes:

- desktop inspect / verify / operate
- repo understand / inspect / verify / propose-fix

## What this release is not

This preview is intentionally **not**:

- a hidden autonomous computer-use agent
- an unrestricted system-control tool
- a silent file-editing agent
- a full multi-agent orchestration system
- a cross-platform desktop release

Windows-first, approval-gated control is the current focus.

## Recommended screenshots for the GitHub release

- `docs/assets/readme/dreamaxis-chat.png`
- `docs/assets/readme/dreamaxis-runtime.png`

## Recommended docs to link in the release

- `README.md`
- `docs/chat-acceptance-report-v0.2.md`
- `docs/desktop-runtime-v1.md`
- `docs/desktop-host-validation-2026-03-24.md`
- `docs/vnext-desktop-operator-first-plan.md`
