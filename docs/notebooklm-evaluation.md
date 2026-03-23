# notebooklm-py evaluation for DreamAxis

## Recommendation

Treat `notebooklm-py` as an **optional integration candidate**, not a DreamAxis core dependency.

## Why it is interesting

The package exposes an unofficial Python API / CLI around NotebookLM workflows such as:

- source import
- notebook-style chat and research
- artifact generation / export
- agent-oriented usage patterns

These ideas align with parts of DreamAxis that are still evolving:

- knowledge source ingestion
- research-oriented skill packs
- notebook-like grouping of source material
- exportable operator artifacts

## Why it should stay optional for now

- it is **unofficial**
- it depends on **undocumented Google APIs**
- long-term stability is not guaranteed
- it would add an external dependency to a system that is currently strongest as a local-first, self-hosted execution platform

## Most useful takeaways for DreamAxis

### 1. Knowledge workflow ideas

- source sets grouped around a task
- notebook-style organization of imported material
- artifact/export thinking for research outputs

### 2. Skill-pack ideas

- external research pack
- source synthesis pack
- notebook-backed summarization or briefing pack

### 3. UX ideas

- better grouping of uploaded docs + web captures + repo notes
- more explicit “research session” framing
- export-ready reports and summaries

## Suggested future shape

If DreamAxis integrates it later, prefer:

- a separate external skill or connector
- user-managed auth
- opt-in research workflow only
- no hard dependency in the default repo-copilot path

## Explicit non-goal for the current phase

Do **not** make NotebookLM:

- the default chat backend
- the default knowledge store
- a required part of local-first DreamAxis setup
