# DreamAxis Repo Copilot Runbook

This runbook validates DreamAxis Chat as a **local-first repo copilot** instead of a generic chatbot.

## Current acceptance status

- date: `2026-03-23`
- provider baseline: `NVIDIA Build`
- v0.2 chat-first scenario pack: `8/8` passed
- NVIDIA repo-copilot scenario pack: `9/9` passed

Primary evidence:

- `docs/chat-acceptance-report-v0.2.md`
- `docs/chat-acceptance-report-nvidia.md`

## Core scenarios

### 1. Repo onboarding

Prompt examples:

- `What is this repo and how do I start it?`
- `Summarize the main module, entrypoint, and key dependencies.`

Expected behavior:

- chat produces a repo-onboarding trace
- CLI probes inspect root structure, manifests, and README or architecture docs
- final answer uses the four response sections:
  - `Intent / plan`
  - `What ran`
  - `What was found`
  - `Recommended next step`

### 2. Verify local readiness

Prompt examples:

- `Is this workspace ready to run locally?`
- `What environment prerequisites are missing here?`

Expected behavior:

- chat surfaces machine readiness + workspace readiness
- environment doctor evidence appears in the trace
- answer includes concrete install or repair hints

### 3. Trace a feature or bug surface

Prompt examples:

- `Where is /dashboard implemented?`
- `Trace the provider settings flow.`

Expected behavior:

- chat routes into repo trace mode
- safe search probes run through the CLI runtime
- answer references real files or matches from the repo

### 4. Run verification workflow

Prompt examples:

- `Verify the dashboard route and capture the result.`
- `Run lint/build and tell me what failed.`

Expected behavior:

- chat runs safe lint/build probes when available
- browser runtime captures a screenshot when a URL or route is present
- runtime executions appear in `/runtime`

### 5. Knowledge-assisted troubleshooting

Prompt examples:

- `Why is this build failing with "X"?`
- `Troubleshoot this route error and suggest the next debugging step.`
- `Propose a safe fix path for this verification lane without changing files.`

Expected behavior:

- chat collects repo evidence first
- knowledge references appear when enabled
- answer stays grounded in the captured execution trace
- `propose_fix` remains **proposal only**:
  - no file writes
  - no mutating shell commands
  - visible targets / suggested commands / risk notes

## Validation targets

Run the scenario pack against at least:

1. `DreamAxis` itself
2. a Node.js repo
3. a Python repo

Recommended NVIDIA validation defaults:

- chat model: `qwen/qwen3-coder-480b-a35b-instruct`
- fallback chat model: `moonshotai/kimi-k2-instruct-0905`
- embedding model: `nvidia/llama-3.2-nv-embedqa-1b-v2`

Docker note:

- if the CLI worker is running in Docker, only repos mounted into the container are directly executable
- the validation script mirrors external target repos into `artifacts/validation-workspaces/` so multi-repo acceptance can still run through the mounted `/workspace` tree
- for day-to-day use on arbitrary local repos, prefer either:
  - running the CLI worker on the host, or
  - adding explicit repo mounts to the worker container

Host-worker note:

- use `scripts/start-host-worker.ps1` on Windows when a workspace root points at a real host path such as `D:\paperclip`
- the host worker registers as a separate runtime so DreamAxis can prefer it over the Docker-mounted worker for Windows-native repo paths
- this avoids the mirror-copy workaround during normal operator use

Companion docs:

- `docs/nvidia-provider-setup.md`
- `docs/notebooklm-evaluation.md`
- `scripts/run_nvidia_repo_copilot_validation.py`

## Acceptance checklist

- chat exposes a visible mode for the turn: `understand`, `inspect`, `verify`, or `propose_fix`
- chat emits `execution_trace`, `runtime_execution_ids`, `artifact_summaries`, and `recommended_next_actions`
- each turn carries an `execution_bundle_id` and parent/child runtime linkage
- only safe read-oriented probes are auto-executed
- high-risk write actions are still blocked
- `propose_fix` returns proposal-only output and clearly marks `not_applied=true`
- `/chat`, `/runtime`, and `/skills` all show a consistent execution story
- when using NVIDIA Build, provider connection status and model binding are visible without leaking secrets
