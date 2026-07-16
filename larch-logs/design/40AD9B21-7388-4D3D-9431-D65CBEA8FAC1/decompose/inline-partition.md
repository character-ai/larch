## Pieces

### Piece 1: Baseline ratchet implementation
- Scope: Add `--baseline`, `--write`, `--initial-reason` flags to `python/larch/lint/duplicate_code.py`; implement baseline check and write logic (cluster key derivation, content hash, stale/new/grown detection); add `regen-duplicate-code-baseline` Makefile target and update `py-lint-duplicate-code` to pass `--baseline`; add all new baseline tests to `python/tests/lint/test_duplicate_code.py`.
- Firm-headings: python/larch/lint/duplicate_code.py, python/tests/lint/test_duplicate_code.py, Makefile
- Acceptance: `python3 -m pytest python/tests/lint/test_duplicate_code.py -q` passes; `python3 python/cli.py lint duplicate-code --help` shows `--baseline`/`--write`/`--initial-reason`; `make py-lint-duplicate-code` still exits 0 when no `--baseline` is passed (backward-compatible).
- Dependencies: none
- Size estimate: ~700 diff lines

### Piece 2: Initial baseline and CI re-enablement
- Scope: Run `make regen-duplicate-code-baseline` to create and commit `python/duplicate-code-baseline.json` (115 clusters); re-enable `push: main` trigger in `.github/workflows/duplicate-code.yaml`, raise `timeout-minutes` to 25, add `issues: write` permission and failure-tracking step; update `py-lint-duplicate-code` call in workflow to use committed baseline.
- Firm-headings: python/duplicate-code-baseline.json, .github/workflows/duplicate-code.yaml
- Acceptance: `make py-lint-duplicate-code` exits 0 on today's main with the committed baseline; `actionlint .github/workflows/duplicate-code.yaml` passes; committed baseline has ≥115 rows each with a non-empty reason.
- Dependencies: blocked-by Piece 1
- Size estimate: ~1000 diff lines (baseline JSON dominates)
