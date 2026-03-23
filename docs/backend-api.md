# DreamAxis Backend API

## Auth and app configuration

### `GET /api/v1/app-config`

Returns:

- `auth_mode`
- `default_workspace_id`
- `runtime_types`
- `feature_flags`
- `environment_profile`

## Environment doctor

### `GET /api/v1/environment`

Returns:

- desktop baseline profile
- known runtime types
- runtime doctor snapshots

### `GET /api/v1/environment/doctor`

Query:

- `workspace_id?`

Returns:

- machine baseline capabilities
- workspace readiness
- install guidance
- skill compatibility summary

### `GET /api/v1/environment/workspaces/{workspaceId}`

Returns workspace-scoped readiness only.

### `POST /api/v1/auth/bootstrap`

Available only when:

- `AUTH_MODE=local_open`

Returns:

- local JWT
- local owner user profile

### `POST /api/v1/auth/login`

Available in both modes, but primarily used when:

- `AUTH_MODE=password`

## Provider connections

### `GET /api/v1/provider-connections`

Lists provider connections for the current user.

### `POST /api/v1/provider-connections`

Creates a new OpenAI-compatible connection.

### `PATCH /api/v1/provider-connections/{id}`

Updates:

- `name`
- `base_url`
- `api_key`
- `is_enabled`
- `default_model_name`
- `default_embedding_model_name`
- `manual_models`

### `POST /api/v1/provider-connections/{id}/test`

Runs a health check against the connection.

### `POST /api/v1/provider-connections/{id}/sync-models`

Attempts `/models` discovery.

### `GET /api/v1/provider-connections/{id}/models`

Returns discovered and manual models.

## Skill packs

### `GET /api/v1/skill-packs`

Query:

- `workspace_id?`

### `POST /api/v1/skill-packs/sync`

Query:

- `workspace_id` (required)

Syncs builtin pack manifests into the database.

### `POST /api/v1/skill-packs/import`

Body:

```json
{
  "workspace_id": "workspace-main",
  "source_path": "D:/my-pack"
}
```

Imports a local manifest or manifest-containing directory.

## Knowledge packs and documents

### `GET /api/v1/knowledge`

Query:

- `workspace_id?`
- `source_type?`
- `knowledge_pack_slug?`

### `POST /api/v1/knowledge/upload`

Multipart form:

- `workspace_id`
- `file`

Supported file types:

- `.txt`
- `.md`
- `.pdf`

### `GET /api/v1/knowledge-packs`

Query:

- `workspace_id?`

### `POST /api/v1/knowledge-packs/sync`

Query:

- `workspace_id` (required)

## Conversations and messages

### `GET /api/v1/conversations`

### `GET /api/v1/conversations/{conversationId}`

### `POST /api/v1/conversations`

Supports:

- `workspace_id`
- `provider_connection_id`
- `model_name`
- `use_knowledge`

### `PATCH /api/v1/conversations/{conversationId}`

Supports:

- `title`
- `provider_connection_id`
- `model_name`
- `use_knowledge`

### `GET /api/v1/messages`

### `POST /api/v1/messages`

### `POST /api/v1/messages/stream`

Streaming assistant route with OpenAI-compatible output.

### SSE event contract

- `message_start`
- `delta`
- `finish`
- `error`
- `done`

`finish` may include:

- `message_id`
- `content`
- `runtime_execution_id`
- `sources`
- `usage`
- `provider_connection_name`
- `model_name`

## Skills

### `GET /api/v1/skills`

Query:

- `workspace_id?`

Returned fields include pack metadata:

- `pack_slug`
- `pack_version`
- `is_builtin`
- `tool_capabilities`
- `knowledge_scope`
- `required_capabilities`
- `recommended_capabilities`
- `workspace_requirements`
- `compatibility`

### `PATCH /api/v1/skills/{skillId}`

Supports:

- `enabled`
- `skill_mode`
- `required_runtime_type`
- `session_mode`
- `command_template`
- `working_directory`
- `agent_role_slug`
- `provider_connection_id`
- `model_name`
- `allow_model_override`
- `use_knowledge`

### `POST /api/v1/skills/{skillId}/run`

Skill execution path depends on `skill_mode`:

- `prompt` → provider-backed prompt execution
- `cli` → CLI runtime dispatch
- `browser` → Browser runtime dispatch

## Runtime control plane

### `GET /api/v1/runtimes`

Query:

- `workspace_id?`
- `runtime_type?`

### `POST /api/v1/runtimes/register`

Runtime worker registration endpoint.

Registration now accepts runtime execution capabilities plus nested environment snapshot data.

### `POST /api/v1/runtimes/{id}/heartbeat`

Runtime worker heartbeat endpoint.

Heartbeat may also refresh:

- `capabilities_json`
- `doctor_status`
- `last_capability_check_at`

### `GET /api/v1/runtime-sessions`

Query:

- `workspace_id?`
- `session_type?`

### `POST /api/v1/runtime-sessions`

Creates a CLI runtime session via the dispatcher.

### `POST /api/v1/runtime-sessions/{id}/close`

Closes a runtime session.

### `GET /api/v1/runtime-executions`

Query:

- `workspace_id?`
- `conversation_id?`

### `GET /api/v1/runtime-executions/{executionId}`

### `POST /api/v1/runtime-executions/{executionId}/dispatch-cli`

### `POST /api/v1/runtime-executions/{executionId}/dispatch-browser`

## Agent roles

### `GET /api/v1/agent-roles`

Returns:

- role metadata
- allowed runtime types
- allowed skill modes
- default skill pack slugs
- default knowledge pack slugs
