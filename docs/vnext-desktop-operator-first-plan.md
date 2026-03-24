# DreamAxis vNext: Desktop Operator First

## Product stance

DreamAxis vNext moves from a repo-copilot-led product into a **Windows-first local desktop operator** with a specialized repo lane.

Core guardrails stay unchanged:

- local-first
- no-signup by default
- runtime-backed audit
- gated actions
- proposal-only for code and file changes

This is **not** a black-box autonomous-computer-use release. The goal is a visibly grounded operator console that can inspect, verify, and perform approved desktop actions with traceable evidence.

## What is already live

The next version should build on the capabilities that are already working locally today:

- Windows host Desktop Runtime v1 is registered and online
- approval-gated desktop actions already validated end to end:
  - `focus_window`
  - `launch_app`
  - `press_hotkey`
  - `type_text`
  - `click`
- `/chat` already renders grounded target, approval state, runtime bundle linkage, and desktop evidence
- `/runtime` already shows selected execution detail, parent linkage, desktop session events, and action artifacts

That means vNext is a **productization and expansion step**, not a reset.

## What to absorb from Agent-S and DeerFlow

### Agent-S ideas to keep

- explicit split between lead agent, grounding, and reflection
- grounding as a first-class structure rather than hidden prompt glue
- bounded reflection after evidence collection
- clear separation between read-only inspection and local action lanes

### DeerFlow ideas to keep

- workflow-first orchestration
- artifact-first outputs instead of prose-first chat
- context compression between workflow stages
- human approval as a real workflow node
- operator-friendly progress visibility

### What not to copy yet

- full multi-agent fanout as the default UX
- hidden long retry loops
- opaque planner chains
- day-one general autonomy across the whole desktop

## Dual-lane model

DreamAxis should expose two visible lanes in `/chat`:

### Desktop Operator lane

- `inspect_desktop`
- `verify_desktop`
- `operate_desktop`

### Repo Copilot lane

- `understand_repo`
- `inspect_repo`
- `verify_repo`
- `propose_fix`

Mode selection can still auto-route by default, but the chosen mode must stay visible and user-switchable per turn.

## Execution contract

Every turn should follow the same auditable path:

1. classify intent
2. build grounding context
3. choose initial probe or action plan
4. create approval gate if any action changes state
5. execute safe probes or approved steps
6. analyze evidence
7. run at most one helper reflection pass if needed
8. return answer, artifacts, and next step

This keeps DreamAxis close to an operator console, not a generic chat page.

## Grounding model

### Desktop grounding v1

Desktop grounding should collect:

- OS version and device summary
- monitor and resolution info
- process list
- top-level windows
- foreground window
- screenshot summary
- OCR / extracted text
- accessibility-tree or UI-node summary when available
- prompt-derived targets like app, window, control, setting, URL, command

Suggested shared types:

- `DesktopGroundingSignal`
- `DesktopGroundedTarget`
- `DesktopActionRequest`
- `DesktopActionApproval`
- `DesktopExecutionArtifact`

### Reflection model

Reflection is helper-only and bounded:

- trigger only when the first probe is ambiguous, blocked, or degraded
- allow only one reflection pass
- use it to narrow the next probe or stop with a clearer operator recommendation

## Runtime shape

DreamAxis should operate three runtime lanes:

1. CLI Runtime
2. Browser Runtime
3. Desktop Runtime v1

### Desktop Runtime v1 scope

Windows only for the first alpha.

Initial capabilities:

- list windows
- inspect focused window
- focus window
- launch allowlisted app
- capture screen
- OCR / extract text
- inspect accessibility or UI summary
- click target
- type text
- press hotkeys
- read system / process / device info

### Policy defaults

Auto-allowed:

- inspect-only desktop actions
- screenshots
- OCR
- window/process/system enumeration

Approval-required:

- launch app
- focus window
- click
- type
- hotkeys
- navigation inside apps

Blocked:

- destructive actions
- silent admin changes
- hidden retry loops
- unrestricted system control

## UI direction: operator motion console

This release should treat motion and compression as product features, not polish-only extras.

### Motion principles

- use Framer Motion with shared motion tokens
- stream sections progressively
- animate workflow stage transitions
- compress completed low-signal steps automatically
- pin the active, failing, or approval-relevant step
- favor subtle rails and pulses over noisy spinners

### `/chat` should show

- sticky operator header
- execution strip
- grounded target panel
- approval card
- compressed evidence chips
- reflection panel
- proposal panel for repo changes only

### `/runtime` should stay the audit plane

It should show:

- parent/child bundle relationships
- desktop action lineage
- grouped timelines
- screenshot / OCR / extract artifacts
- approval history

The current runtime detail view is already good enough to anchor this direction; the next step is to compress and prioritize it rather than redesign it from scratch.

## Versioned rollout

### v0.3.0-alpha.1 — desktop grounding foundation

Build:

- desktop modes
- desktop grounding payloads
- desktop runtime registration
- read-only desktop probes
- desktop-aware traces

Acceptance:

- enumerate windows and processes
- capture screenshot and OCR
- return grounded desktop targets in chat

### v0.3.0-alpha.2 — approval and controlled operations

Build:

- desktop action request contract
- approval-needed payloads
- allowlisted focus / launch / click / type / hotkey actions
- action lineage in runtime

Acceptance:

- one low-risk desktop action can be requested and confirmed
- no unapproved action executes
- audit trail is visible in chat and runtime

### v0.3.0-alpha.3 — motion UI and compression

Build:

- shared motion tokens
- execution strip
- compressed cards
- artifact thumbnails
- approval card polish
- runtime audit density improvements

Acceptance:

- active turns feel live without clutter
- users can understand a turn without reading walls of output
- approval, failure, and active step stay visually dominant

### v0.3.0-beta — helper workflow fusion

Build:

- helper reflection
- compressed context handoffs
- browser + terminal + VS Code scenarios
- repo/desktop fusion turns

Acceptance:

- desktop and repo lanes feel coherent
- reflection narrows follow-up probes correctly
- code changes remain proposal-only

## Desktop alpha scenario pack

Minimum Windows validation:

1. inspect desktop
2. verify desktop with screenshot + OCR
3. operate desktop with approval
4. inspect browser + terminal + VS Code in one grounded summary
5. keep repo verify / troubleshoot / propose_fix working without regression

## Immediate implementation priorities

The first implementation wave after this planning pass should focus on:

1. strengthen desktop grounding summaries and target selection
2. improve approval-card clarity and requested-action previews in chat
3. compress runtime detail so the active execution, parent bundle, and artifacts are readable at a glance
4. add motion primitives for stage transitions, active execution focus, and evidence arrival
5. validate browser + terminal + VS Code as the first polished desktop triad

## Non-goals

Do not ship these in the first desktop-first milestone:

- hidden autonomous retry loops
- unrestricted computer-use autonomy
- silent file editing
- automatic code application
- cross-platform parity before Windows proves out
- exposed multi-agent swarm UX
