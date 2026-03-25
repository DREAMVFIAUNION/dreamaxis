# DreamAxis v0.3.0-alpha.2 Acceptance Report

- Date: `2026-03-25`
- Branch under test: `codex/v0.3-stage-b`
- Scope: alpha.2 acceptance / release-readiness verification for the already-implemented operator workflow
- Raw evidence source: `artifacts/acceptance/alpha2-results.json`

## Executive summary

DreamAxis `v0.3.0-alpha.2` passed the acceptance target for this round.

- Total recorded scenarios: `9`
- Result summary: `9 pass / 0 partial / 0 fail / 0 blocked`
- Operator scenarios: `4/4 pass`
- Repo scenarios: `5/5 pass`

This round verifies that DreamAxis now behaves as:

- an **OperatorPlan-backed desktop operator**
- a **chat-first live control surface**
- an **operator queue and approval surface**
- a **runtime-backed audit plane**
- a **proposal-only repo lane** that still avoids unapproved code writes

## Preflight gate re-check

The preflight gates were re-run before acceptance:

- `git status --short` was clean before acceptance execution
- `python -m compileall apps/api/app apps/desktop-worker/app` passed
- `pnpm --filter @dreamaxis/web build` passed

Environment evidence recorded in `alpha2-results.json` confirms:

- required workspaces present:
  - `workspace-main`
  - `workspace-e8e98dd05c`
- required runtimes present:
  - `runtime-cli-local`
  - `runtime-browser-local`
  - `runtime-cli-host-local`
  - `runtime-desktop-local`

## Acceptance matrix

### 1. Inspect desktop

- Result: `pass`
- Workspace: `workspace-e8e98dd05c`
- Conversation: `conversation-8ca51ff74a`
- Operator plan: `oplan-732972e55106`
- Parent runtime execution: `runtime-7fb726f3d8da`
- Mode/template: `inspect_desktop` / `inspect-active-desktop`

Evidence:

- captured system info
- enumerated top-level windows
- captured focused window
- captured process list
- verification summary: `Using explicit desktop mode for desktop inspection.`

Conclusion:

- desktop inspect flow executed end to end with runtime-backed artifacts and no approval requirement

### 2. Verify browser surface

- Result: `pass`
- Workspace: `workspace-e8e98dd05c`
- Conversation: `conversation-055f9e20e1`
- Operator plan: `oplan-413cb65dcf62`
- Parent runtime execution: `runtime-55e1f2e83d45`
- Child runtime executions:
  - `runtime-002af3704803`
  - `runtime-55e1f2e83d45`
- Template: `verify-browser-surface`

Evidence:

- browser-surface verification artifacts recorded on the plan
- runtime lineage linked back to the parent execution
- verification summary present on the plan trace

Conclusion:

- browser verification remains functional inside the operator-plan workflow and produces audit-ready evidence

### 3. Operate with approval

- Result: `pass`
- Workspace: `workspace-e8e98dd05c`
- Conversation: `conversation-e4d0238c4f`
- Operator plan: `oplan-ee29531433dd`
- Parent runtime execution: `runtime-c135846481cd`
- Child runtime executions:
  - `runtime-86e69abb181a`
  - `runtime-b87f3b69f20c`
  - `runtime-c135846481cd`
- Mode: `operate_desktop`
- Prompt: `Focus Chrome, press ctrl+l, and type "https://example.com".`

Approval transition evidence:

- before approval:
  - status: `pending_approval`
  - pending approval count: `1`
  - operator stage: `approval`
- after approval:
  - status: `completed`
  - operator stage: `complete`

Evidence:

- approval history persisted on the OperatorPlan
- operate step did not continue until approval was posted
- runtime lineage linked the operator plan to child executions
- verification summary present after execution

Conclusion:

- approval gating, approval persistence, and post-approval resume all worked in a real desktop operate scenario

### 4. Browser + Terminal + VS Code triad

- Result: `pass`
- Workspace: `workspace-e8e98dd05c`
- Conversation: `conversation-fd53af8336`
- Operator plan: `oplan-f039c4d3f135`
- Parent runtime execution: `runtime-b9eb9d2cddfe`
- Child runtime executions:
  - `runtime-1eb276c6cbd9`
  - `runtime-48eff77a34ca`
  - `runtime-3e57f01d4f45`
  - `runtime-b9eb9d2cddfe`
- Template: `browser-terminal-vscode-triad`

Evidence:

- multiple child executions linked back to one operator plan
- artifact summaries recorded for the triad capture
- plan-level verification summary recorded

Conclusion:

- the multi-surface triad path is working as a grouped operator-plan workflow instead of an isolated single action

### 5. Failure + reflection narrowing

- Result: `pass`
- Workspace: `workspace-main`
- Conversation: `conversation-9f5bdcc807`
- Runtime execution: `runtime-9382afdf02fe`
- Mode: `verify_repo`
- Prompt: `Verify http://127.0.0.1:3999/ and explain the failure with the next grounded probe.`

Evidence:

- trace summary status: `failed`
- `failure_summary` present
- `primary_failure_target` present: `/workspace`
- `stderr_highlights` present
- `reflection_summary` present

Key recorded failure summary:

> Lint probe failed because the required local toolchain is not available in the active runtime.

Conclusion:

- bounded failure analysis still produces grounded narrowing instead of silently looping or fabricating success

### 6. Repo lane non-regression

#### 6.1 understand_repo

- Result: `pass`
- Conversation: `conversation-abed28e9c1`
- Runtime execution: `runtime-951c50015a8c`
- Mode: `understand_repo`

#### 6.2 inspect_repo

- Result: `pass`
- Conversation: `conversation-5bbbbcdd3b`
- Runtime execution: `runtime-eb504759f1ac`
- Mode: `inspect_repo`

#### 6.3 verify_repo

- Result: `pass`
- Conversation: `conversation-c0504bf0d2`
- Runtime execution: `runtime-a0a1a8ac8976`
- Mode: `verify_repo`

#### 6.4 propose_fix

- Result: `pass`
- Conversation: `conversation-246090e36c`
- Runtime execution: `runtime-f633b6732e87`
- Mode: `propose_fix`

Repo-lane evidence:

- repo scenarios still emit runtime execution ids
- non-proposal repo modes did **not** emit proposal payloads
- `propose_fix` returned a proposal with `not_applied: true`

Conclusion:

- the repo lane did not regress and still respects the proposal-only rule for code and file changes

## UI validation

The three public operator surfaces were checked against the alpha.2 split:

- `/chat` = live operation and approval-aware execution console
- `/operator` = approval queue, active runs, templates, and plan management
- `/runtime` = audit plane with lineage, artifacts, and execution detail

Color semantics remained aligned with the intended mapping:

- active = blue
- approval = orange
- failed = red

### Screenshot evidence

Local capture sources:

- `artifacts/acceptance/alpha2-chat-approval.png`
- `artifacts/acceptance/alpha2-operator-queue.png`
- `artifacts/acceptance/alpha2-runtime-audit.png`

Promoted canonical docs assets:

- `docs/assets/readme/dreamaxis-chat.png`
- `docs/assets/readme/dreamaxis-operator.png`
- `docs/assets/readme/dreamaxis-runtime.png`

Observed UI outcomes:

- chat clearly surfaced the current operator plan, approval banner, and runtime linkage
- operator clearly surfaced pending approval cards and active-run summaries
- runtime clearly surfaced audit lineage and artifact-heavy execution review instead of raw logs alone

## Acceptance fixes made during this round

The acceptance run exposed two implementation issues that were fixed before finalizing evidence:

1. `apps/api/app/api/v1/operator_plans.py`
   - eager-loaded `Conversation.provider_connection`
   - fixed async lazy-load failure during `POST /api/v1/operator-plans`

2. `apps/api/app/services/operator_plan_executor.py`
   - aggregated step-level `approval` payloads into `plan.approvals_json`
   - restored approval history visibility on completed plans

An additional reusable runner was added:

- `scripts/run_alpha2_acceptance.py`

## Release-readiness decision

Release recommendation: **ready after final doc/assets preflight**

Why:

- all acceptance scenarios are recorded
- all recorded scenarios passed
- operator plan, approval gate, runtime lineage, deterministic grounding, bounded reflection, and repo proposal-only behavior all have evidence
- README screenshot refresh is justified because alpha.2 introduces clearly visible operator-first product surfaces

Required final release actions:

1. update tracked docs and screenshots
2. re-run compile + web build
3. confirm working tree state
4. tag `v0.3.0-alpha.2`
5. merge `codex/v0.3-stage-b` into `main` only if the final preflight stays green
