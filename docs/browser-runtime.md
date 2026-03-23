# DreamAxis Browser Runtime v1

Browser Runtime v1 brings Playwright execution into the same control-plane model already used by CLI runtime.

## Goal

DreamAxis should not stop at prompt + CLI workflows. Browser Runtime adds a second execution surface for:

- webpage inspection
- form interaction
- page text extraction
- link extraction
- screenshot capture
- future browser-assisted agent roles

## Architecture

Browser Runtime keeps the same three-layer shape:

- `runtimes`
- `runtime_sessions`
- `runtime_executions`

Implemented service:

- `apps/browser-worker`

This worker:

- registers as a `browser` runtime host
- heartbeats back to the API
- creates or reuses browser sessions
- executes Playwright actions
- returns artifacts back into execution storage

## Supported actions in v1

- `open_url`
- `click`
- `hover`
- `type`
- `select_option`
- `press`
- `wait_for`
- `extract_text`
- `extract_links`
- `take_screenshot`
- `list_tabs`
- `close_tab`

These are still intentionally limited for the first open-source release, but they now cover a more useful set of real browser tasks.

## Execution flow

1. a Browser skill is selected in `/skills`
2. the skill renders a JSON action list
3. the API validates the action allowlist
4. the dispatcher selects an online `browser` runtime
5. a reusable or new browser session is chosen
6. the browser worker executes the action list
7. artifacts and extracted text are returned to the API
8. `runtime_executions` is updated with browser metadata
9. `/runtime` shows screenshots and extracted content

## Artifact model

Current browser artifacts may include:

- screenshot data URLs
- tab listings
- extracted links
- current URL and title

Artifacts are stored in `artifacts_json` on the execution row for MVP simplicity.

## Example builtin browser skill

`core-browser-playwright` ships with pack entries such as:

```json
[
  { "action": "open_url", "url": "https://example.com" },
  { "action": "wait_for", "time": 1 },
  { "action": "extract_text" },
  { "action": "extract_links", "selector": "a", "limit": 10 },
  { "action": "take_screenshot", "name": "capture" }
]
```

## Worker configuration

Important env vars:

```env
ENABLE_BROWSER_RUNTIME=true
BROWSER_WORKER_PUBLIC_URL=http://browser-worker:8200
BROWSER_WORKER_SCOPE_REF_ID=workspace-main
BROWSER_WORKER_HEADLESS=true
```

## Current limits

Browser Runtime v1 does **not** yet include:

- arbitrary JS evaluation
- browser profiles per user
- remote browser grids
- stealth / anti-bot layers
- persistent artifact storage outside execution JSON
- full browser agent planning/orchestration

## Why this matters for DreamAxis

Browser Runtime is part of the long-term DreamAxis positioning:

- local-first
- self-hosted
- runtime-pluggable
- skill-pack driven
- ready for future role-based agent execution
