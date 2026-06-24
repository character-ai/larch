## Proposed Design Outline

### Goals
- Halve the word count of the anti-halt preamble in both `skills/implement/SKILL.md` and `skills/design/SKILL.md`.
- Preserve all skill-specific content: contract token, step-sequence chain, Critical boundary callouts, and non-sequential control-flow carve-outs.
- Ensure `make lint` (including `test-anti-halt-banners`) passes unchanged.

### Non-goals
- No behavior change; terser prose only.
- Do not touch `skills/shared/subskill-invocation.md` or the canonical anchor.
- Do not update `scripts/test-anti-halt-banners.sh` (contract tokens are preserved verbatim).

### Approach sketch
- Identify the shared-anchor text duplicated inline in each banner: the "strictly subordinate" clause, "A normal sequential `proceed to Step N+1`…" clause, and "Every relevant-checks helper call…" clause.
- Remove those duplicates from both banners.
- For `/design`, additionally cut: the verbose Step 5c recap-summary elaboration (the "The only orchestrator-text addition permitted…" paragraph and "**Not** gated on…") and the "Step 1e Gate A is reachable only via re-entry…" structural note (already in Step 1e body).
- Leave all Critical boundaries, carve-outs, and step-sequence chains verbatim.

### Surfaces in scope
- `skills/implement/SKILL.md` (line 14 banner)
- `skills/design/SKILL.md` (line 29 banner)

### Open questions
- None.
