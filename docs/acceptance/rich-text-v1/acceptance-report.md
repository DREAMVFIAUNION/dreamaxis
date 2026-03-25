# Rich Text v1 acceptance report

Date: 2026-03-25

## Result

- Web build: PASS
- Acceptance harness route: `/acceptance/rich-text-v1`
- Screenshot set: PASS
- Deterministic fixtures: PRESENT

## Verified behavior

- Streaming assistant messages render through the rich renderer in tolerant mode.
- Mermaid failure state shows an error card and visible source block.
- Markdown / GFM tables / code highlighting / KaTeX / Mermaid are covered by fixed fixtures.
- Operator and runtime explanatory text surfaces are covered by dedicated screenshot fixtures.
- Raw logs remain monospace and are not markdown-rendered.
- Narrow-width capture is included as a required artifact.

## Screenshot artifacts

Stored in `docs/acceptance/rich-text-v1/screenshots/`:

- `chat-01-streaming-rich.png`
- `chat-02-markdown-basics.png`
- `chat-03-code-highlight.png`
- `chat-04-math-katex-all-syntax.png`
- `chat-05-mermaid-success.png`
- `chat-06-mermaid-fallback-with-src.png`
- `chat-07-html-escaped.png`
- `chat-08-narrow-viewport.png`
- `operator-01-plan-summary-rich.png`
- `operator-02-failure-summary-rich.png`
- `runtime-01-execution-summary-rich.png`
- `runtime-02-approval-summary-rich.png`
- `runtime-03-raw-logs-monospace.png`

## Notes

- The acceptance route is fixture-driven and does not depend on live backend responses.
- The screenshot harness is intended for pre-main verification and can be rerun locally after future renderer changes.
