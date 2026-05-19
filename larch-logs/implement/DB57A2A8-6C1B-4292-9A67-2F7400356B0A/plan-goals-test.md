## Goal
Add transient-retry observability to failure-log entries in launch-review.sh

## Implementation Plan

### Context
PR #2357 added a transient-retry loop (TRANSIENT_ATTEMPT counter) to scripts/launch-review.sh. Code
inspection confirms the retry IS firing (TRANSIENT_ATTEMPT is present, external_is_transient_infra_failure
is defined, MAX_TRANSIENT_RETRIES=2). However, append_launch_failure logs only AUTH_ATTEMPT as
"retries=N", making TRANSIENT_ATTEMPT invisible in execution-issues.

### Goal
Extend the failure-log format to surface both auth-retries and transient-retries when both are
provided, so operators can tell whether the transient-retry mechanism fired from the log line alone.

### Files to modify

1. **scripts/append-tool-failure.sh** (~12 lines changed)
   - Add `TRANSIENT_RETRY_COUNT=""` variable alongside existing `RETRY_COUNT`
   - Add `--transient-retry-count` flag to the while-loop parser
   - Update the header_suffix composition (lines 131-137):
     - When RETRY_COUNT + TRANSIENT_RETRY_COUNT both set: `auth-retries=N, transient-retries=M`
     - When only RETRY_COUNT (backward compat for other callers): keep `retries=N`
     - When neither: no suffix change

2. **scripts/launch-review.sh** (~6 lines changed)
   - `append_launch_failure` helper: add 7th positional arg `transient_retry_count`
   - Pass `--transient-retry-count "$transient_retry_count"` to append-tool-failure.sh when non-empty
   - Codex call site (line 547): append `"$TRANSIENT_ATTEMPT"` as 7th arg
   - Cursor call site (line 957): append `"$TRANSIENT_ATTEMPT"` as 7th arg

3. **scripts/append-tool-failure.md** (~5 lines changed)
   - Document --transient-retry-count: optional, produces `transient-retries=N` in the header suffix
   - Note that when both --retry-count and --transient-retry-count are set, format changes to
     `auth-retries=N, transient-retries=M` to distinguish the two retry dimensions

4. **scripts/test-launch-review.sh** (~80 lines added)
   Add 3 new cases after the existing SL-transient-* block (before "Restore normal codex stub"):

   **Case SL-transient-obs-exhausted** (extends SL-transient-retry-exhausted):
   - Same stub (exits 7 with empty output always)
   - Set IMPLEMENT_TMPDIR so append_launch_failure actually writes
   - Assert: (a) launcher exits non-zero, (b) exactly ONE failure entry in execution-issues,
     (c) failure line contains `transient-retries=3` (TRANSIENT_ATTEMPT increments to 3 after 2 retries
     with MAX_TRANSIENT_RETRIES=2: start=1, +1 for retry1=2, +1 for retry2=3, then 3>2 → break)

   **Case SL-transient-obs-fired** (extends SL-transient-retry-codex-7):
   - Same stub (exits 7 on attempt 1, succeeds on attempt 2)
   - Set IMPLEMENT_TMPDIR
   - Assert: (a) launcher exits 0, (b) execution-issues has NO failure entry for codex-review

   **Case SL-transient-obs-nontransient** (new):
   - Stub: exits 1, writes 5KB to the output file (not stderr); exit code 1 not in transient allowlist
   - Set IMPLEMENT_TMPDIR
   - Assert: (a) exactly 1 invocation (no retry), (b) ONE failure entry in execution-issues,
     (c) failure line does NOT contain `transient-retries=`

### Edge cases
- `--transient-retry-count` is optional; callers that don't pass it retain the existing `retries=N` format
- TRANSIENT_ATTEMPT=1 on both success and non-transient failure paths: the issue states "When the value
  is 1, no retry fired (or the original attempt succeeded — but then there'd be no failure log)".
  So `transient-retries=1` in a failure log means: the transient-retry mechanism evaluated but decided
  not to retry (the failure was not transient-infra-shaped).


## Test plan
- Run `bash scripts/test-launch-review.sh --tool codex` → all assertions including 3 new ones pass
- Grep `transient-retries` in append-tool-failure.sh to confirm field appears in output
- Run `make lint-bash32` to verify no Bash 4+ constructs introduced
- Run `/relevant-checks` (agent-lint + pre-commit)
