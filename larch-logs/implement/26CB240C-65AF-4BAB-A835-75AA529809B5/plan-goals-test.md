## Goal
Implement issue #4417: [IMPLEMENTING] [Bug] plan-review panel always panel-failed: embedded plan-review-loop.sh still references deleted collect-agent-results.sh.

## Implementation Plan
## Summary

Every `/design` Step 3 plan-review panel fails with `LOOP_STATUS=panel-failed` and `COLLECT_OK_COUNT=0` on the current `main`. All 12 reviewer slots are marked `status=failed` in `reviewer-status.tsv` even though the reviewers completed and their `.done` sentinels exist with valid output.

## Root Cause

Commit `a850ee1eb` (PR #4401, "sh-to-py C1a4: Results collector and retry contracts") deleted `scripts/collect-agent-results.sh` and ported it to `python/cli.py agent collect-results`. It did **not** update the embedded `plan-review-loop.sh` Bash script stored as a gzip+base64 blob in `python/plan_review.py._LEGACY_ASSETS`.

The embedded script line 18 still reads:

```bash
PLAN_REVIEW_COLLECT_SH="${LARCH_PLAN_REVIEW_COLLECT_SH:-$PLUGIN_ROOT/scripts/collect-agent-results.sh}"
```

`plan_review._run_legacy` materializes a temp root and symlinks `scripts/` from the live plugin dir. Since `scripts/collect-agent-results.sh` was deleted, the symlinked path does not exist. When the loop calls:

```bash
_collect_out=$(LARCH_QUIET_DISABLE=1 "$PLAN_REVIEW_COLLECT_SH" --timeout "$COLLECT_TIMEOUT" ... --paths-file "$PANEL_PATHS_FILE" 2>"$_collect_err_tmp")
_collect_rc=$?
```

the shell fails to execute the missing script, `_collect_rc` is non-zero, `_collect_out` is empty, `_collect_parseable=0`, and the code at line 1247 sets `LOOP_STATUS=panel-failed` and returns 1.

Because `_collect_rc != 0` with empty stdout occurs **before** `_count_collector_evidence()` records any OK/failure counts, both `COLLECT_OK_COUNT` and `COLLECT_FAILURE_COUNT` stay at their initialized `0`. The `_write_reviewer_status_artifact` call then sets every reviewer slot's `status=failed` (the default, since no collect records exist to override it).

**Note**: `plan-review-collector.stderr` is empty because the script is never even executed — there is no stderr to capture. The `.done` sentinels and output files are present and valid; the collector simply never ran.

## Impact

**Every `/design` Step 3 plan review fails silently.** All reviewer output is ignored. The run is treated as `panel-failed` (Gate B bypassed, proceed to Step 3b). Operators have no signal that the panel ran and produced findings.

Confirmed on the `/design` session for issue #4407 (PR #4408): all 12 reviewers (6 Cursor + 6 Codex) produced valid TSV output in under 250 seconds, but `COLLECT_OK_COUNT=0` was recorded and the session resolved with `panel-failed`.

## Suggested Fix

Update the embedded `plan-review-loop.sh` in `python/plan_review.py._LEGACY_ASSETS` to invoke `python3 "$PLUGIN_ROOT/python/cli.py" agent collect-results` directly instead of the deleted Bash wrapper. The `PLAN_REVIEW_COLLECT_SH` variable is invoked as a single quoted command (`"$PLAN_REVIEW_COLLECT_SH" --timeout ...`), so the simplest repair is either:

1. Replace the variable-path invocation with a direct inline call:
   ```bash
   _collect_out=$(LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" agent collect-results \
       --timeout "$COLLECT_TIMEOUT" \
       --substantive-validation \
       --validation-mode \
       --structured-reviewer-validation \
       --paths-file "$PANEL_PATHS_FILE" 2>"$_collect_err_tmp")
   ```

2. Or introduce a thin wrapper script at `scripts/collect-agent-results.sh` that delegates to the Python CLI, preserving the existing `PLAN_REVIEW_COLLECT_SH` override hook.

Option 1 is simpler and avoids re-introducing the deleted Bash file.

The `LARCH_PLAN_REVIEW_COLLECT_SH` env override used in tests and the existing `plan-review-loop.sh` integration branch in the test suite should be updated or retired accordingly.

## Reproduction

Run `/design <any-issue>` → Step 3 plan review executes all reviewers → all `.done` files written → `reviewer-status.tsv` shows all slots `status=failed elapsed_s=<N>` → `LOOP_STATUS=panel-failed` → Gate B bypassed.

## Test plan
(no test plan section in plan-file)
