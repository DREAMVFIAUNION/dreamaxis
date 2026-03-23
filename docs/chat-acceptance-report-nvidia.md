# DreamAxis NVIDIA Chat Acceptance Report

## Provider validation

- Connection ID: `conn-f281cbfc3e73`
- Test status: `active`
- Test message: Connection is valid and model discovery succeeded.
- Sync count: `189`
- Sync warning: None
- Chat model: `qwen/qwen3-coder-480b-a35b-instruct`
- Embedding model: `nvidia/llama-3.2-nv-embedqa-1b-v2`

## Knowledge upload

- Upload status: `ready`
- Chunk count: `1`
- Error message: None

## Scenario results

| Repo | Scenario | Result | Provider | Sections | Trace | Runtime | Knowledge | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DreamAxis | repo-onboarding | PASS | ok | ok | ok | ok | ok | ok |
| DreamAxis | environment-readiness | PASS | ok | ok | ok | ok | ok | ok |
| DreamAxis | feature-trace | PASS | ok | ok | ok | ok | ok | ok |
| DreamAxis | verification-workflow | PASS | ok | ok | ok | ok | ok | ok |
| DreamAxis | knowledge-assisted-troubleshooting | PASS | ok | ok | ok | ok | ok | ok |
| Paperclip | repo-onboarding | PASS | ok | ok | ok | ok | ok | ok |
| Paperclip | environment-readiness | PASS | ok | ok | ok | ok | ok | ok |
| Brain Core | repo-onboarding | PASS | ok | ok | ok | ok | ok | ok |
| Brain Core | environment-readiness | PASS | ok | ok | ok | ok | ok | ok |

## Summary

- Passed: `9`
- Blocked: `0`
- Degraded: `0`

## Next fixes

- Promote the NVIDIA Build setup flow into README/provider docs and keep monitoring free-tier stability.
