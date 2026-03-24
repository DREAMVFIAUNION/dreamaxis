# DreamAxis v0.2 Chat-first Acceptance Report

## Validation baseline

- Provider connection: `NVIDIA Build`
- Provider status: `active`
- Test status: `active`
- Test message: Connection is valid and model discovery succeeded.
- Chat model: `qwen/qwen3-coder-480b-a35b-instruct`
- Embedding model: `nvidia/llama-3.2-nv-embedqa-1b-v2`
- API base: `http://127.0.0.1:8000`

## Scenario matrix

| Repo | Scenario | Mode | Result | Mode | Trace | Evidence | Grounding | Proposal | Browser | Troubleshooting | Failure target | Reflection | Runtime linkage | Safety | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DreamAxis | understand-onboarding | `understand_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| DreamAxis | inspect-provider-settings | `inspect_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| DreamAxis | verify-dashboard | `verify_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| DreamAxis | propose-fix-chat | `propose_fix` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Paperclip | verify-readiness | `verify_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Paperclip | inspect-entrypoint | `inspect_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Brain Core | verify-readiness | `verify_repo` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| Brain Core | propose-fix-startup | `propose_fix` | PASS | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |

## Screenshot anchors

- `verify-dashboard` conversation: `/chat/conversation-9dbf29822e`
- `propose-fix-chat` conversation: `/chat/conversation-1826888b7f`

## Summary

- Passed: `8`
- Failed: `0`

## Next fixes

- v0.2 grounded verify loop is passing with visible grounding targets, reflection-aware follow-up probes, proposal-only edits, and runtime-linked evidence across the acceptance set.
