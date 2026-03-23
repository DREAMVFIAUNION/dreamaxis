# Skill Environment Requirements

DreamAxis skills can now declare explicit environment requirements.

## Skill fields

Each skill definition may include:

- `required_capabilities`
- `recommended_capabilities`
- `workspace_requirements`

## Behavior

### Required capabilities

If a required machine capability is missing, the skill is **blocked**.

Examples:

- `git`
- `node`
- `python`
- `browser_runtime`

### Recommended capabilities

If a recommended capability is missing, the skill can still run but receives a **warning**.

Examples:

- `docker`
- `playwright`

### Workspace requirements

If a workspace requirement is missing, the skill is **blocked** even if the machine baseline is fine.

Examples:

- `safe_root`
- `workspace_repo`
- `node_project`
- `python_project`
- `docker_project`

## Builtin pack conventions

- `core-cli` → safe local execution / repo inspection
- `core-browser-playwright` → browser runtime + Playwright
- `core-repo` → repo + Node/project-aware inspection
- `core-docs` → mostly prompt-driven, low machine dependency
- `core-knowledge` → prompt + retrieval
- `core-research` → prompt-first analysis

## Operator experience

The skill compatibility snapshot is shown on:

- `/skills`
- `/environment`

If a skill is blocked, DreamAxis should explain the exact missing capability instead of failing silently.
