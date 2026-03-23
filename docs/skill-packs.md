# DreamAxis Skill Packs

Skill Packs turn DreamAxis skills into portable, syncable capability bundles.

## Source types

DreamAxis currently recognizes three pack origins:

- `builtin` - shipped inside the repo
- `imported` - loaded from a local folder or checked-out git repo
- `workspace` - reserved for future in-app authoring flows

## Why packs exist

Packs let DreamAxis behave more like an execution platform than a single prompt app:

- skills can be versioned
- builtin capabilities can be synced into the database
- community packs can be imported without a central marketplace
- roles can bind to packs by default

## Builtin packs shipped today

- `core-cli`
- `core-browser-playwright`
- `core-research`
- `core-docs`
- `core-knowledge`
- `core-repo`

These packs cover high-frequency local-first workflows such as:

- repo inspection
- git status
- docker checks
- document generation
- browser automation
- knowledge-assisted operations

Recent builtin coverage includes examples for:

- browser click-and-capture flows
- browser search snapshots with extracted links
- browser selector extraction
- dropdown/select workflows
- workspace search
- README preview
- package script inventory
- git diff stat
- release notes drafting
- issue triage summaries

## Pack manifest shape

Builtin and imported packs use JSON manifests.

High-level fields:

- `slug`
- `name`
- `version`
- `description`
- `tool_capabilities`
- `skills`

Each skill can define:

- `name`
- `slug`
- `description`
- `skill_mode`
- `required_runtime_type`
- `session_mode`
- `command_template`
- `working_directory`
- `agent_role_slug`
- `tool_capabilities`
- `knowledge_scope`
- `input_schema`

## Runtime model

Skill definitions synced from packs are stored in the database so the UI can:

- enable / disable them
- bind provider connections and models
- execute them
- attach runtime history

Key runtime-facing fields:

- `skill_mode = prompt | cli | browser`
- `required_runtime_type`
- `tool_capabilities`
- `knowledge_scope`
- `pack_slug`
- `pack_version`
- `is_builtin`

## API

### List packs

`GET /api/v1/skill-packs?workspace_id=workspace-main`

### Sync builtin packs

`POST /api/v1/skill-packs/sync?workspace_id=workspace-main`

### Import a local pack

`POST /api/v1/skill-packs/import`

Example body:

```json
{
  "workspace_id": "workspace-main",
  "source_path": "D:/my-dreamaxis-pack"
}
```

`source_path` may point to:

- a manifest file
- a directory containing `dreamaxis.skill-pack.json`
- a directory containing `skill-pack.json`

## UI workflow

Open `/skills` to:

1. sync builtin packs
2. import a custom pack
3. inspect the pack registry
4. inspect individual skills
5. bind provider/model/runtime settings
6. execute prompt, CLI, or Browser skills

## Open-source stance

DreamAxis does **not** depend on a hosted marketplace.

The intended community loop is:

1. publish a pack manifest in a git repo
2. users clone it locally
3. import it from `/skills`
