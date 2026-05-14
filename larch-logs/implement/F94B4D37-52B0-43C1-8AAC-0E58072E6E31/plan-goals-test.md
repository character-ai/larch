## Goal
Remove sub-command stdout leaks from ship-pr.sh so its stdout is only KEY=VALUE envelope lines

## Implementation Plan

### Objective
Remove all sub-command stdout leaks from scripts/ship-pr.sh so its stdout consists only of KEY=VALUE envelope lines.

### Root cause
ship-pr.sh captures sub-command output into variables (`out=$(cmd 2>"$fail_file")`), appends it to the fail_file (`printf '%s\n' "$out" >> "$fail_file"`), then ALSO echoes it to ship-pr.sh's own stdout (`printf '%s\n' "$out"`). Separately, `cat "$fail_file"` is used to echo file contents to stdout after some direct-redirect calls. Both patterns bleed sub-command verbosity into the Bash tool result.

### Changes

#### 1. scripts/ship-pr.sh — remove all leaky stdout emits (18 sites)

Remove every `printf '%s\n' "$<var>"` that immediately follows a `printf '%s\n' "$<var>" >> "$fail_file"` line. Also remove all `cat "$fail_file"` lines that echo diagnostic content to stdout.

Affected functions and lines (current):
- `run_checks_phase` line 378: remove `printf '%s\n' "$out"`
- `run_bump_phase` line 399: remove `printf '%s\n' "$classify_out"`
- `run_bump_phase` line 414: remove `printf '%s\n' "$apply_out"`
- `run_bump_phase` line 429: remove `cat "$fail_file"` (check-bump-version)
- `run_bump_phase` line 448: remove `printf '%s\n' "$finalize_out"`
- `run_pr_create_phase` line 584: remove `printf '%s\n' "$out"`
- `run_pr_create_phase` line 605: remove `cat "$fail_file"` (gh-pr-body-update)
- `run_ci_fix_vendor` line 681: remove `printf '%s\n' "$checks_out"` (the grep pipe on line 682 stays)
- `run_ci_fix_vendor` line 692: remove `cat "$fail_file"` (git-commit)
- `run_ci_fix_vendor` line 707: remove `cat "$fail_file"` (git-push)
- `run_evaluate_failure` line 724: remove `printf '%s\n' "$rerun_out"`
- `run_evaluate_failure` line 738: remove `cat "$fail_file"` (gh-run-logs)
- `run_rebase_rebump` line 763: remove `printf '%s\n' "$drop_out"`
- `run_rebase_rebump` line 772: remove `cat "$fail_file"` (larch-log.sh commit)
- `run_rebase_rebump` line 781: remove `printf '%s\n' "$rebase_out"`
- `run_rebase_rebump` line 811: remove `printf '%s\n' "$rebase_out"` (post-conflict rebase)
- `run_rebase_rebump` line 838: remove `printf '%s\n' "$classify_out"`
- `run_rebase_rebump` line 853: remove `printf '%s\n' "$apply_out"`
- `run_rebase_rebump` line 892: remove `cat "$fail_file"` (git-force-push)
- `run_ci_phase` line 926: remove `cat "$fail_file"` (larch-log.sh commit)
- `run_ci_phase` line 944: remove `printf '%s\n' "$out"` (ci-wait)
- `run_ci_phase` line 964: remove `printf '%s\n' "$merge_out"`
- `run_ci_phase` line 999: remove `cat "$fail_file"` (rebase-push fork mode)
- `run_postmerge_phase` line 1044: remove `cat "$fail_file"` (implement-finalize postmerge)

Lines NOT to touch:
- All `printf '%s\n' "$var" >> "$fail_file"` — these save to file for diagnostics, keep them
- All `printf '%s\n' "$var" | grep -q ...` — these are pipes with no stdout, keep them
- `is_transient_net_signature "$(cat "$fail_file" 2>/dev/null)"` — subprocess, not stdout, keep
- All breadcrumb lines like `printf '✅ 8: version bump...'` — legitimate stdout, keep

#### 2. scripts/ship-pr.sh — add FAILURE_DETAIL_LOG to record_failure

In `record_failure`, add a `printf 'FAILURE_DETAIL_LOG=%s\n' "$output_file"` call so the orchestrator knows where to find diagnostic details. This replaces the removed `cat "$fail_file"` as the mechanism for surfacing file paths:

```bash
record_failure() {
    local site=$1 tool=$2 exit_code=$3 output_file=$4 category=${5:-Tool Failures}
    printf 'FAILURE_DETAIL_LOG=%s\n' "$output_file"
    append_tool_failure_local \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$exit_code" \
        --category "$category" \
        --output-file "$output_file"
}
```

#### 3. scripts/test-ship-pr.sh — add stdout-size cap assertion

Add a test case that runs ship-pr.sh through a typical phase (checks phase) with stub helpers and asserts the total stdout length is ≤ 2048 characters. Use the existing stub infrastructure.

#### 4. scripts/ship-pr.md — document FAILURE_DETAIL_LOG

Add documentation of the FAILURE_DETAIL_LOG key to the "Helper Contracts" section.

### What NOT to change
- Do not change the PHASE state machine, BAIL_REASON, STALL_TRACKING, or any existing exit codes
- Do not change how KEY=VALUE parsing works from captured variables (grep/kv_value still works from the variable)
- Do not change fail_file creation or `append_tool_failure_local`
- Do not change any scripts other than ship-pr.sh, test-ship-pr.sh, ship-pr.md


## Test plan
Run /relevant-checks. Verify test-ship-pr.sh passes including the new stdout-size assertion.
