# DreamAxis Doctor

The Doctor page lives at:

- `/environment`

It is the operator-facing readiness console for local execution.

## What it shows

### 1. Machine baseline

- Git
- Node.js
- package manager
- Python
- Docker
- Browser Runtime
- Playwright

### 2. Workspace readiness

- workspace root validity
- git repo detection
- Node project detection
- Python project detection
- Docker project detection

### 3. Skill coverage

How many skills are:

- `ready`
- `warn`
- `blocked`

### 4. Install guidance

DreamAxis collects human-readable hints from detected capability gaps so users know what to install next.

## How to use it

Use Doctor before debugging a failed skill if:

- a repo skill says it cannot run
- a browser skill does not start
- a Docker-related skill returns empty or fails unexpectedly
- a workspace looks mounted but DreamAxis says it is not repo-ready

## Runtime integration

Runtime hosts report environment snapshots during:

- runtime registration
- heartbeat refreshes

That allows DreamAxis to distinguish:

- runtime online and healthy
- runtime online but degraded
- runtime offline
