## Decision 1: Scope subset of suggested fixes
- **Question**: Which subset of the 4 suggested fixes (#1 lint guard, #2 mawk smoke test, #3 CI-fixer diagnostic, #4 stall fallback) is in scope?
- **Resolution**: All four (#1-#4).
- **Source**: user

## Decision 2: Location of the new awk-portability lint
- **Question**: Should #1 add a standalone `scripts/lint-awk-dynamic-regex.sh` or extend `lint-bash32.sh`?
- **Resolution**: New standalone script matching the lint-bash32 / lint-readability-preamble pattern.
- **Source**: user

## Decision 3: Patterns detected by the new lint
- **Question**: Which awk-portability patterns does the new lint detect?
- **Resolution**: `[[:class:]]` in dynamic regex contexts PLUS other mawk gaps — `\xNN` hex escapes, `\d/\w/\s` Perl shorthands, and backreferences (`\1`, `\2`, ...).
- **Source**: user

## Decision 4: Files scanned by the new lint
- **Question**: Which files does the lint scan?
- **Resolution**: Repo-wide `*.sh` and `*.awk` files (excluding `node_modules/`, `larch-logs/`, `.git/`).
- **Source**: user

## Decision 5: CI-fixer strategy (fix #3 reshaped)
- **Question**: Where should the CI-fixer diagnostic improvement plumb in?
- **Resolution**: Strengthen the fixer prompt's autonomous local-reproduce-and-verify loop: ship-pr.sh launches the fixer with instructions to first reproduce the failed CI job locally, then iterate fixes (up to 10 local-fix attempts) until the local run passes. If the fixer cannot reach a local-pass state, it must exit failing; when the fixer fails, ship-pr fails. Verify the fixer has the ability to run tests locally in its sandbox.
- **Source**: user

## Decision 6: Verification layers (fix #4 reshaped)
- **Question**: With the fixer now responsible for autonomous local verification, should ship-pr's existing `_verify_failed_jobs_locally` (post-fix re-run) be kept or dropped?
- **Resolution**: Keep both layers. Fixer must reach local-pass before exiting 0; ship-pr still runs `_verify_failed_jobs_locally` after the fixer returns. Defense-in-depth.
- **Source**: user

## Decision 7: Mawk smoke test scope
- **Question**: Which harnesses should run under `mawk` explicitly in CI?
- **Resolution**: All awk-using lint harnesses (`test-lint-readability-preamble`, `test-lint-bare-grep-probe`, `test-lint-gh-body-inline`, `test-lint-fix-loop`, `test-lint-bash32`, plus the new `test-lint-awk-dynamic-regex`).
- **Source**: user

---

## Correction (post-Step-2b, after operator clarified the actual root cause)

The original Step 1c/1d answers were based on the bug report's hypothesis (`[[:space:]]` in dynamic `match()`). The operator clarified that the hypothesis was wrong:
- The actual cause was the em-dash `—` (U+2014) embedded in a runtime awk regex pattern — both as part of a string passed to `match()` AND as an `awk -v VAR=...em-dash...` value used in `$0 ~ VAR`. Some Ubuntu CI awk builds emit silent warnings to stderr (exit 0, non-empty stderr) on multi-byte UTF-8 chars in dynamic patterns, breaking `assert_lint_ok`'s "expected empty stderr" check.
- PR character-ai/larch#3144 fixed the actual cause by replacing `orchestrator_style_re` (containing `—`) with a plain-ASCII anchor `orchestrator_style_anchor='readability-style.md.**'` used via `command grep -F` and `index($0, anchor)`. The `\x22 → "` fix was a separate real portability issue and stays as a one-off.
- The ship-pr CI-fixer gap is still real: the Cursor CI-fixer was invoked 3 times and produced zero commits; ship-pr looped on `FIX_ATTEMPTS++` until `STALL_STEP=10-max-retries` because the `first-fixer-non-health` Exit 3 path was never reached when Cursor exited 0 without making any working-tree change.

## Decision 1 (corrected): Scope subset
- **Resolution**: Two surfaces only — (A) lint guard for multi-byte UTF-8 in dynamic awk regex patterns, (B) ship-pr `_stage_and_push_ci_fixes` / `run_ci_fix_vendor` no-commit detection. (C) Regression test in `test-ship-pr-fix-loop.sh` for the no-commit classification path is optionally bundled (recommended for completeness).
- **Supersedes**: original Decision 1 (which included #2 mawk smoke test and #3 fixer diagnostic improvement).

## Decision 3 (corrected): Detected patterns
- **Resolution**: Multi-byte UTF-8 bytes inside awk dynamic regex contexts only. Specifically: (a) `awk -v VAR=...` arguments whose value contains any non-ASCII byte, and (b) lines inside `awk '...'` bodies that contain non-ASCII bytes AND a regex-callsite token (`match(`, `gsub(`, `sub(`, `split(`, `~`, `!~`). The `[[:`, `\xNN`, `\d/\w/\s`, and backreference patterns from the original Decision 3 are dropped.
- **Supersedes**: original Decision 3.

## Decision 5 (dropped): CI-fixer prompt local-loop
- **Resolution**: Dropped. The shared `LOCAL_REPRO` invariant already in `launch-{cursor,codex,claude}-ci.sh` is sufficient. The actual gap is in ship-pr's classification of a vendor-exit-0-no-commits outcome.
- **Supersedes**: original Decision 5.

## Decision 6 (dropped): Two verification layers
- **Resolution**: Not relevant under the corrected scope (no prompt change → no fixer-side autonomous loop to weigh against ship-pr's post-fix verification). `_verify_failed_jobs_locally` stays untouched.
- **Supersedes**: original Decision 6.

## Decision 7 (dropped): mawk smoke test in CI
- **Resolution**: Dropped. The underlying bug is not "mawk vs gawk" — it is "multi-byte UTF-8 in dynamic awk regex on some awk builds". The new lint guard catches the source pattern at commit time; a runtime smoke test under mawk would not reproduce the actual em-dash warning because mawk handles `[[:space:]]` differently from the multi-byte warning the operator observed.
- **Supersedes**: original Decision 7.

## Decision 4 (preserved): Files scanned by the new lint
- **Resolution**: Unchanged — repo-wide `*.sh` and `*.awk` (excluding `node_modules/`, `larch-logs/`, `.git/`).

## Decision 2 (preserved): Lint location
- **Resolution**: Unchanged — new standalone script, renamed `scripts/lint-awk-multibyte-regex.sh` for accuracy under the corrected scope.
