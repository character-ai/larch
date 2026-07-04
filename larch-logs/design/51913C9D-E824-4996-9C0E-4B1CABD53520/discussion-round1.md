## Decision 1: `--window` unit
- **Question**: Does `--window N` mean N commits or a calendar duration?
- **Resolution**: N commits — the last N commits that touched `python/skill-closure-baseline.json`. `--since-tag` covers calendar/release-boundary needs via this repo's existing version tags (1,026 `vX.Y.Z` tags found).
- **Source**: user

## Decision 2: Historical schema drift tolerance
- **Question**: Can the ledger reuse the current strict baseline-row validator (`load_baseline` / `_validate_baseline_row` in `lint_skill_closure_growth.py`, which requires an exact 12-key set and exactly today's 4 ratcheted targets) to parse every historical revision of `python/skill-closure-baseline.json`?
- **Resolution**: No. Git history shows the schema evolved: the earliest committed baseline (`9669ad4e8`) has only `design`/`implement` targets and 6 of today's 12 keys; `review`/`panel-tier` and the content-token/conditional fields were added later (most recently by #6156). The ledger needs its own lenient, per-revision parser that reads whatever `skill` + `closure_estimated_tokens` pairs exist in each historical JSON blob, tolerates missing/extra keys and a growing target set, and treats each target's first appearance in history as an initial value rather than a delta. Spot-checking real history confirms this: PR #5978's merge commit shows panel-tier `closure_estimated_tokens` 57,617 → 50,057 (delta -7,560), and PR #5980's merge shows 50,711 → 44,124 (delta -6,587) — both exactly matching the round-XI umbrella issue's (#6166) audited attribution, and landing exactly on the acceptance criterion's 44,124 endpoint.
- **Source**: codebase

## Decision 3: No changes to the existing lint module
- **Question**: Does this feature require modifying `python/larch/lint/lint_skill_closure_growth.py` (the module PR #6156 also touched, per the umbrella's "same module" blocker note)?
- **Resolution**: No. Because the ledger uses its own lenient historical parser (Decision 2) rather than the strict current-tree validator, it only needs the existing `BASELINE_RELPATH` constant. The new ledger logic, CLI verb, and tests live in a new sibling module (`python/larch/lint/skill_closure_ledger.py`); the existing lint/report verbs, their baseline schema, and their tests are untouched.
- **Source**: codebase

## Decision 4: No CI gate
- **Question**: Should the new verb's output (including the optional "raise" marker) ever fail a command or block a merge?
- **Resolution**: No. Per the issue ("No hard gate; do not block feature merges"), the verb always exits 0 for successful reads (matching the existing `skill-closure report` verb's pattern) and is purely informational; it is not wired into `lint skill-closure-growth` or any CI job.
- **Source**: codebase

4 decisions resolved.
