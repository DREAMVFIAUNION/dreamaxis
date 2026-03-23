# DreamAxis Desktop AI Assistant Standard v1

DreamAxis is a **local-first desktop AI assistant platform**.  
That means the local machine is part of the product surface, not just a hidden prerequisite.

## Required baseline

DreamAxis standardizes on the same baseline most desktop coding assistants expect:

- **Git**
- **Node.js**
- **pnpm or npm**
- **Python**

If one of these is missing, the local machine is not considered fully ready.

## Optional execution enhancements

These are not required for every workflow, but they unlock more of DreamAxis:

- **Docker Desktop**
- **Browser Runtime**
- **Playwright browser binaries**
- **Configured shell profile** (`powershell` / `pwsh`)

## Workspace-scoped readiness

DreamAxis also checks the active workspace itself, including:

- workspace root exists
- `.git` present
- `package.json` present
- Python project files (`pyproject.toml`, `requirements.txt`, `setup.py`)
- Docker project files (`Dockerfile`, `docker-compose.yml`, `compose.yml`)

This lets DreamAxis answer:

- “Can this machine run the skill?”
- “Can this workspace support the skill?”

## Status model

DreamAxis uses three statuses:

- `ready` — capability is present and usable
- `degraded` — optional capability is missing or partially available
- `missing` — required capability is missing

## Product surfaces

The standard appears in three places:

- `/environment` — full doctor page
- `/runtime` — runtime host readiness summary
- `/dashboard` — high-level missing/degraded counts

## Why this exists

DreamAxis should do more than fail after the user clicks run.

The product should:

- detect missing tools up front
- explain why a skill is blocked
- suggest how to fix the machine or workspace
- make runtime readiness observable in the UI
