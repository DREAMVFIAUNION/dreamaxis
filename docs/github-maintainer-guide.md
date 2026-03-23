# DreamAxis GitHub Maintainer Guide

Use this doc when setting up or maintaining the public repository.

## Recommended labels

Core labels:

- `bug`
- `enhancement`
- `documentation`
- `good first issue`
- `help wanted`
- `question`
- `needs reproduction`
- `blocked`

Area labels:

- `area:web`
- `area:api`
- `area:runtime-cli`
- `area:runtime-browser`
- `area:skills`
- `area:knowledge`
- `area:docs`
- `area:auth`

Priority labels:

- `p0`
- `p1`
- `p2`

## Suggested milestones

Suggested first milestones:

### `v0.1.x polish`

- docs cleanup
- provider UX fixes
- runtime acceptance hardening
- screenshot/release polish

### `v0.2.x operator usefulness`

- more builtin skills
- better Browser Runtime ergonomics
- stronger knowledge workflows

### `v0.3.x execution maturity`

- policy/safety hardening
- richer artifacts and audit history
- pack import/version improvements

## Recommended issue triage flow

1. verify the report is reproducible
2. assign an area label
3. assign a priority label
4. decide whether it belongs in current milestone
5. request logs/screenshots if needed

## Good first issues

Best starter issues usually involve:

- docs clarifications
- UI empty/error states
- pack metadata cleanup
- small runtime/logging improvements
- README polish

## Public repo defaults to preserve

When reviewing contributions, protect these defaults:

- `AUTH_MODE=local_open` remains the default
- no forced signup in default path
- provider keys remain self-hosted
- local Docker path remains first-class
- builtin skill packs and knowledge packs keep working from a fresh clone
