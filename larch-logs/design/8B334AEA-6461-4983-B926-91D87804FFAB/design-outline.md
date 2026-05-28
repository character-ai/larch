## Proposed Design Outline

### Goals
- Catch the multi-byte-UTF-8-in-dynamic-awk-regex class of portability bugs at commit time.
- Make ship-pr classify "vendor exit 0 with no working-tree change" as `first-fixer-non-health` so the autonomous main-agent CI-fix sub-procedure actually fires instead of looping `FIX_ATTEMPTS++` to a silent `STALL_STEP=10-max-retries`.
- Regression-cover the no-commit classification path in `test-ship-pr-fix-loop.sh`.

### Non-goals
- Re-fix the upstream `lint-readability-preamble.sh` em-dash pattern (PR #3144 owns that).
- Add a mawk-vs-gawk CI smoke test (the failure mode is multi-byte handling per awk build, not "mawk uses different regex syntax").
- Strengthen the fixer prompt with a local-reproduce-and-iterate loop (existing `LOCAL_REPRO` invariant stays).
- Touch `_verify_failed_jobs_locally` or `lint-bash32.sh` semantics.
- Refactor `run_ci_fix_vendor` control flow beyond the surgical HEAD-non-advance check.

### Approach sketch
- Add `scripts/lint-awk-multibyte-regex.sh` + sibling `.md` + harness `.sh` + `.md`. Scans repo-wide `*.sh` and `*.awk`. Flags two patterns: `awk -v VAR=...<non-ASCII bytes>...` and lines inside `awk '...'` bodies that contain non-ASCII bytes AND a regex-callsite token (`match(`, `gsub(`, `sub(`, `split(`, `~`, `!~`). Same-line pragma `# lint-awk-multibyte-regex: ok <reason>` (reason required) suppresses.
- Modify `run_ci_fix_vendor` in `scripts/ship-pr.sh` to capture HEAD SHA before the tier loop, and after the winning tier's `_stage_and_push_ci_fixes` returns 0, compare to the new HEAD. If HEAD did not advance, the vendor produced no fix: emit a warn breadcrumb, set `BAIL_REASON=first-fixer-non-health` (with a detail-log capture explaining `vendor-exit-0-no-commits`), and return non-zero so `run_evaluate_failure`'s existing first-fixer-non-health branch routes to Exit 3 → autonomous main-agent CI-fix.
- Add one fixture case to `scripts/test-ship-pr-fix-loop.sh`: a stub vendor that exits 0 and stages nothing; assert `BAIL_REASON=first-fixer-non-health` is written and `run_ci_fix_vendor` returns non-zero.
- Wire `Makefile` `lint:` umbrella + `.PHONY` + `test-harnesses-N:` shard for the new lint; one `CHANGELOG.md` bullet.

### Surfaces in scope
- `scripts/lint-awk-multibyte-regex.sh` (NEW), `scripts/lint-awk-multibyte-regex.md` (NEW), `scripts/test-lint-awk-multibyte-regex.sh` (NEW), `scripts/test-lint-awk-multibyte-regex.md` (NEW).
- `scripts/ship-pr.sh` (HEAD-non-advance detection inside `run_ci_fix_vendor`).
- `scripts/test-ship-pr-fix-loop.sh` (no-commit-classification regression).
- `Makefile` (target + harness wiring).
- `CHANGELOG.md`.

### Open questions
- None.
