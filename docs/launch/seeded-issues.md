# DreamAxis Seeded Issues for Public Collaboration

These issue seeds are meant for the first public contribution wave and align with:

- milestone: `v0.1.x polish`
- labels: `good first issue`, `documentation`, `area:*`, `p1/p2`, `help wanted`

They are intentionally small, concrete, and safe for external contributors.

---

## 1. Improve provider onboarding hints in `/settings/providers`

**Suggested labels**

- `enhancement`
- `area:web`
- `area:docs`
- `p1`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

The provider settings flow works, but first-time users still need clearer guidance on:

- what "OpenAI-compatible" means
- when to sync models vs enter one manually
- which fields are required for a successful connection

Improve the provider settings UX copy and empty/help states so a new user can configure their first connection with less guesswork.

**Acceptance hints**

- clearer field helper text
- safer empty-state wording
- no raw provider jargon in the first-run path

---

## 2. Polish README and docs cross-linking for first-time contributors

**Suggested labels**

- `good first issue`
- `documentation`
- `area:docs`
- `p2`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

The public README is much stronger now, but contributor navigation can still improve.

Review README + docs links and tighten:

- docs grouping
- contributor-friendly next steps
- where to find runtime/browser/provider docs quickly

Focus on navigation and clarity, not major product rewrites.

**Acceptance hints**

- fewer "where do I click next?" moments
- clearer path from README to deeper docs
- no broken or redundant doc links

---

## 3. Improve runtime empty/error states in the web console

**Suggested labels**

- `enhancement`
- `area:web`
- `area:runtime-cli`
- `area:runtime-browser`
- `p1`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

The runtime console already exposes hosts, sessions, executions, and artifacts, but some empty/error states still need better operator-facing UX.

Improve runtime console states for cases such as:

- no executions yet
- runtime temporarily offline
- execution failed with limited details
- browser artifact not available

The goal is better operator readability without hiding important context.

**Acceptance hints**

- clearer empty states
- clearer failure summaries
- no dead-end panels

---

## 4. Add more metadata polish to builtin skill cards

**Suggested labels**

- `good first issue`
- `enhancement`
- `area:skills`
- `p2`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

Builtin skill cards should make it easier to understand:

- required capabilities
- recommended capabilities
- runtime type
- intended role / use case

Improve the presentation of skill metadata in the UI so users can decide faster which skill to run.

**Acceptance hints**

- required vs recommended is visually distinct
- runtime type is easy to scan
- no extra clicks required to understand basic compatibility

---

## 5. Tighten screenshot/documentation consistency

**Suggested labels**

- `documentation`
- `area:docs`
- `p2`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

DreamAxis now uses tracked canonical README screenshots under `docs/assets/readme/` and keeps acceptance exports in `artifacts/acceptance/`.

Audit screenshot-related docs and make sure:

- README references only canonical assets
- screenshot docs explain the refresh workflow clearly
- release/docs language stays consistent about README vs release assets

**Acceptance hints**

- no public docs point README rendering at gitignored paths
- screenshot refresh process is obvious to maintainers

---

## 6. Improve first-run guidance on the Doctor / Environment page

**Suggested labels**

- `enhancement`
- `area:web`
- `area:auth`
- `p1`

**Suggested milestone**

- `v0.1.x polish`

**Issue draft**

The Environment / Doctor page already explains machine and workspace readiness, but it could do a better job guiding first-run users from "missing capability" to "next action."

Improve the page with clearer:

- install hints
- severity hierarchy
- "what should I do next?" guidance

The page should help users recover faster instead of just reporting status.

**Acceptance hints**

- missing required capabilities feel actionable
- optional degraded states feel understandable
- first-run users can self-serve more easily
