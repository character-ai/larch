## Proposed Design Outline

### Goals
- New read-only CLI verb reporting per-merge eager-token (`closure_estimated_tokens`) deltas per target from `python/skill-closure-baseline.json`'s git history: commit, PR, delta.
- Summary mode (`--window N` commits, or `--since-tag TAG`) aggregating deltas per target for release notes/round planning.
- Visible marker on commits that raise any target's eager baseline (informational only).

### Non-goals
- No CI gate or exit-code change; never blocks merges.
- No changes to `lint_skill_closure_growth.py`'s scan/validate/lint behavior or its baseline schema.
- No new lint, no wiring into `lint skill-closure-growth`.

### Approach sketch
- New sibling module `python/larch/lint/skill_closure_ledger.py`; new `("skill-closure", "ledger")` CLI verb.
- New `git.py` helper (`Runner`-based, raising) listing commits touching a path with sha+subject.
- Own lenient per-revision JSON parser (skill + `closure_estimated_tokens` only) tolerating historical schema drift (older revisions had fewer targets/fields) — does not reuse the strict current-tree baseline validator.
- Track per-target "first seen" state so a target's historical introduction reports as initial, not a delta.

### Surfaces in scope
- `python/larch/lint/skill_closure_ledger.py` (new)
- `python/larch/git/git.py` (new helper)
- `python/larch/cli.py` (registry entry)
- `python/tests/lint/test_skill_closure_ledger.py` (new, fixture git repo)
- `docs/run-log-cli.md` (new section)

### Open questions
- None.
