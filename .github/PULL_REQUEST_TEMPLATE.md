## Summary

- what changed:
- why it changed:

## Validation

- [ ] `python -m compileall apps/api/app apps/worker/app apps/browser-worker/app`
- [ ] `pnpm --filter @dreamaxis/web build`
- [ ] docker/local smoke path completed if relevant

## Product/default checks

- [ ] default `AUTH_MODE=local_open` behavior still works
- [ ] no secrets are exposed in logs or API/UI payloads
- [ ] docs updated for behavior/config changes

## Screenshots / artifacts

If UI/runtime behavior changed, add screenshots or artifact notes.

## Follow-up work

List anything intentionally deferred.
