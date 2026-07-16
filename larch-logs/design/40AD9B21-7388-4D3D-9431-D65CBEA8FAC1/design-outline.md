## Proposed Design Outline

### Goals
- Revive the R0801 duplicate-code check as a shrink-only baseline ratchet on `push: main`.
- Gate new and grown clusters while grandfathering 115 existing ones in a reason-bearing `python/duplicate-code-baseline.json`.
- Make failures actionable with a tracked GitHub issue so the check cannot silently die again.

### Non-goals
- PR-time changed-files mode (deferred; separate issue).
- Eliminating existing duplicate clusters (baseline drain is follow-on work).
- Changes to `python/.pylintrc` thresholds or detection semantics.

### Approach sketch
- Extend `python/larch/lint/duplicate_code.py` with `--baseline` / `--write` / `--initial-reason` flags and baseline check/write logic. Key each cluster by sorted module tuple + normalized content hash (per G-Det-1); stale rows and new/grown clusters fail.
- Add `python/duplicate-code-baseline.json` (created by `make regen-duplicate-code-baseline`; initial reason blanket-grandfathers all 115 clusters).
- Add `regen-duplicate-code-baseline` Makefile target; update `py-lint-duplicate-code` to pass `--baseline`.
- Re-enable `push: main` trigger in `.github/workflows/duplicate-code.yaml`, raise `timeout-minutes` to 25, add `issues: write` permission and a failure step that creates or updates one tracking issue.

### Surfaces in scope
- `python/larch/lint/duplicate_code.py` (extended, no new module)
- `python/tests/lint/test_duplicate_code.py` (new baseline tests)
- `python/duplicate-code-baseline.json` (new file, committed after initial regen)
- `Makefile` (new regen target, updated py-lint-duplicate-code target)
- `.github/workflows/duplicate-code.yaml` (trigger + timeout + failure step)

### Open questions
- None.
