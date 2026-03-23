# NVIDIA Build provider setup for DreamAxis

DreamAxis can use NVIDIA Build as a standard **OpenAI-compatible** provider connection.

## Recommended defaults

- **Name**: `NVIDIA Build`
- **Provider type**: `openai_compatible`
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Default chat model**: `qwen/qwen3-coder-480b-a35b-instruct`
- **Fallback chat model**: `moonshotai/kimi-k2-instruct-0905`
- **Default embedding model**: `nvidia/llama-3.2-nv-embedqa-1b-v2`

## Provider Settings flow

1. Open `/settings/providers`
2. Create a new connection
3. Enter the base URL and API key
4. Save the connection
5. Run **Test connection**
6. Run **Sync models**
7. If model discovery is partial, keep the connection and manually add:
   - one chat model
   - one embedding model
8. Bind the connection to:
   - the workspace default, or
   - the active conversation lane

## Expected statuses

- `active`: connection and model discovery succeeded
- `manual_entry_required`: connection is reachable but `/models` is incomplete or unsupported
- `requires_config`: missing API key
- `error`: transport/auth/provider failure

## NVIDIA validation notes

- DreamAxis does **not** need a custom NVIDIA adapter
- chat, SSE, skill runs, and knowledge embeddings all reuse the same OpenAI-compatible adapter path
- chat model and embedding model may differ
- the current pgvector schema expects a 1536-dimension embedding, so `nvidia/llama-3.2-nv-embedqa-1b-v2` is the safest NVIDIA default for end-to-end validation today
- free-tier or shared-tier availability may vary by model, so keep a fallback chat model ready

## Safety

- never commit the NVIDIA API key to the repo
- never include the key in screenshots, issue comments, release notes, or logs
- if a key has been pasted in a public place, rotate it before ongoing use
