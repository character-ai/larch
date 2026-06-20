## Proposed Design Outline

### Goals
- Add a public `/deps` skill that audits all open issues and groups them by title-prefix state: DESIGNING, DESIGNED, IMPLEMENTING, REGULAR.
- Refresh REGULAR issues conservatively against latest main, and infer cross-issue dependencies semantically, wiring new edges through `/block-issue`.
- Gate every GitHub mutation (body rewrites, stale closes, block-edges) behind one operator approval.

### Non-goals
- No autonomous mutation. Nothing is edited, closed, or blocked without approval.
- No combining or deduplicating issues. That is `/combine-issues`; `/deps` only refreshes, closes-if-fully-stale, and links.
- No new blocked-by edge added TO an in-flight issue (DESIGNING/DESIGNED/IMPLEMENTING). Their existing edges are untouched.

### Approach sketch
- New public skill `skills/deps/SKILL.md` drives the flow; mechanical work lives in a new `python/cli.py deps` verb set (`python/deps_audit.py`), LLM judgment stays prompt-side. Mirrors the `/combine-issues` split.
- Reuse existing helpers: `gh resolve-repo` for the target repo, `block-issue add-blocked-by` / `issue add-blocked-by` for edges, redaction plus `gh issue edit --body-file` for rewrites.
- Python does fetch, state-grouping, existing-edge read, and the mutating writes; prompt-side does actuality/accuracy assessment, full-semantic dependency inference, and rewrite composition.
- Apply the in-flight flip rule (block the REGULAR side instead) and a loud warning when both endpoints are in-flight.

### Surfaces in scope
- `skills/deps/SKILL.md` (new public skill, trigger-bearing description)
- `python/deps_audit.py` + `python/cli.py deps` wiring + `python/test_deps_audit.py`
- Skill registration and docs: README skill catalog, `docs/topology.md` + `skills/shared/topology.tsv`, plugin/marketplace manifest

### Open questions
- Full-semantic detection is O(n^2) over the backlog. Default to bounding candidate pairs with a logged cap (like `/combine-issues` Tier-2) to control token cost? Recommended: yes.
