## Goal
Implement issue #5698: [IMPLEMENTING] [BUG] Packaging migration importer scan misses skills/**/*.py that sys.path-extend python/.

## Implementation Plan
## Summary

During the flat-module packaging migration (#5655), the importer scan was scoped only to `python/` and missed `skills/fluff-analysis/scripts/fluff-analysis.py`, which imports `self_review_tally_items` using the flat name. The flat module was deleted but the skill script's import was not updated, causing a `ModuleNotFoundError` in the `test-fluff-analysis-corpus` CI harness.

## Original report

During issue #5655 implementation, the grep scan for flat module importers searched only `python/` but missed `skills/fluff-analysis/scripts/fluff-analysis.py` which contains `from self_review_tally import self_review_tally_items`. This flat import survived to CI, causing a `ModuleNotFoundError` in the `test-fluff-analysis-corpus` harness. Root cause: the implementation grep was scoped to `python/` only, while `fluff-analysis.py` adds `python/` to `sys.path` and imports flat modules directly. A broader scan of all `.py` files under `skills/` should be part of the "repoint all importers" step in any flat-module packaging migration.

## Reproduction scenario

1. Run any flat-module packaging migration (`python/` scope grep for importers).
2. Exclude `skills/` from the grep.
3. Delete the flat module.
4. CI runs `test-fluff-analysis-corpus`, which invokes `skills/fluff-analysis/scripts/fluff-analysis.py`.
5. `ModuleNotFoundError: No module named 'self_review_tally'`.

## Expected behavior

Every flat module importer — including those in `skills/**/*.py` scripts that add `python/` to `sys.path` — is found and updated before the flat module is deleted.

## Observed behavior

`skills/fluff-analysis/scripts/fluff-analysis.py` retained `from self_review_tally import self_review_tally_items` after `python/self_review_tally.py` was deleted. CI failed with:

```
ModuleNotFoundError: No module named 'self_review_tally'
  File "skills/fluff-analysis/scripts/fluff-analysis.py", line 34
```

## Root cause analysis

Two patterns colluded:

1. **Scope gap**: the importer scan used `grep -r ... python/ --include="*.py"`, which correctly covers `python/larch/**` and `python/test_*.py` but is blind to `skills/` scripts.
2. **sys.path extension pattern**: `skills/fluff-analysis/scripts/fluff-analysis.py` (and `skills/voter-calibration/scripts/voter-calibration.py`) extend `sys.path` with the `python/` directory at runtime, making flat module names importable. This is a legitimate pattern (documented in `skills/fluff-analysis/scripts/pyrightconfig.json` via `extraPaths`) but it creates an implicit dependency on flat-root availability that the migration grep did not capture.

The `docs/python-migration.md` hard-cutover rule ("all consumers (skills, docs, Makefile, CI) are repointed in the same commit") already implies skills scripts must be included, but the implementation step did not operationalize this — no grep over `skills/` was run.

## Evidence

- `skills/fluff-analysis/scripts/fluff-analysis.py` line 28-34: sets `sys.path.insert(0, python_dir)` then does `from self_review_tally import ...`
- `skills/fluff-analysis/scripts/pyrightconfig.json`: `"extraPaths": ["../../../python"]` — confirms IDE-level awareness that flat names are importable
- `skills/voter-calibration/scripts/voter-calibration.py`: same `sys.path` insert pattern, but already uses `larch.*` imports (not affected this time)
- `docs/python-migration.md` package-layout note: "all consumers (skills, docs, Makefile, CI) are repointed in the same commit"

## Affected files

- `skills/fluff-analysis/scripts/fluff-analysis.py` — was the missed importer (fixed in #5655 CI-fix commit)
- `docs/python-migration.md` — should be strengthened to document that `skills/**/*.py` must be included in importer scans
- Any future packaging migration plan / design document that lists the "repoint importers" step

## Suggested fix(es)

1. **Widen the importer grep in packaging migrations**: scan `python/ skills/ .claude/skills/` (and any other directory whose `.py` files may `sys.path`-extend `python/`) not just `python/`.
2. **Add a lint rule or acceptance criterion**: after deleting a flat module, assert `grep -r "from <module> import\|import <module>" python/ skills/ .claude/skills/ --include="*.py"` returns no matches.
3. **Document in `docs/python-migration.md`**: explicitly call out `skills/**/*.py` and `.claude/skills/**/*.py` as consumer directories that must be included in importer scans, alongside the existing "all consumers" language.

## Open questions

- Should a pre-commit lint check verify that no `skills/` Python file imports a known-deleted flat module name? Or is a post-deletion grep check in the implementation checklist sufficient?
- Are there other directories (e.g. `hooks/`, `.github/`) that contain `.py` files extending `sys.path` to `python/`?

## Test plan
(no test plan section in plan-file)
