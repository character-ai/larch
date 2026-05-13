## Goal
Fix ci-wait.sh to use a poll-count budget so laptop suspend does not trigger a false bail (Part A), and add a new exit 6 transient-net retry path in ship-pr.sh so transient network errors can be retried by the orchestrator (Part C).

## Implementation Plan

### Part A — suspend-resilient ci-wait.sh timeout

**File**: `scripts/ci-wait.sh`

1. Before the polling loop, compute `MAX_POLLS=$((TIMEOUT / 10))`.
2. Replace the `$SECONDS -ge $TIMEOUT` guard at the top of the while loop with `$checks -ge $MAX_POLLS`.
3. At the top of each iteration, record `iter_start=$(date +%s)`. After `sleep 10`, compute `iter_delta=$(( $(date +%s) - iter_start ))`. If `iter_delta > 60`: emit `"⚠ suspend detected — iteration took ${iter_delta}s, not counting toward poll budget"` to stderr and decrement `checks` by 1 so the long iteration does not consume a poll slot.
4. Keep `$SECONDS` only for the ELAPSED= stdout field and the dot-progress lines (no behavioral effect on timeout logic).

**New file**: `scripts/test-ci-wait.sh` — offline regression harness with 4 cases:
- *happy path*: stub `ci-status.sh` returns `CI_STATUS=pass` → `ACTION=merge` after first poll.
- *pending-then-pass*: stub returns `CI_STATUS=pending` 3 times, then `CI_STATUS=pass` → `ACTION=merge` after 4th poll.
- *suspend simulation*: stub returns `CI_STATUS=pending`, but first iteration sleeps 65s (or simulated via mocked `date`); verify the script does NOT bail on timeout and the second call (returning `CI_STATUS=pass`) drives `ACTION=merge`. Because we can't easily sleep 65s in a test, instead stub `date` to return a large delta on the first call (iter_start=0, then 70 on next call).
- *genuine timeout*: stub always returns `CI_STATUS=pending`. Use `--timeout 30` → `MAX_POLLS=3`. Assert bail after 3 polls with `BAIL_REASON` containing "Wall-clock timeout".

**New file**: `scripts/test-ci-wait.md` — sibling stub pointing to `scripts/ci-wait.md`.

Add `make test-ci-wait` target to Makefile (or confirm it already has a pattern).

### Part C — transient-retry exit code 6 in ship-pr.sh

**File**: `scripts/ship-pr.sh`

1. After `exit_stall()`, add two helpers:
```bash
exit_transient_net() {
    state_set_many BAIL_REASON "$1" STALL_TRACKING false
    exit 6
}

is_transient_net_signature() {
    local text=$1
    case "$text" in
        *"Could not resolve"*|*"unable to access"*|*"Connection refused"*|*"Temporary failure"*|*"timed out"*|*"TLS handshake"*|*"HTTP 5"*|*"Wall-clock timeout"*|*"no valid output 3 times"*|*"git fetch"*"failed"*|*"network/auth issue"*) return 0 ;;
        *) return 1 ;;
    esac
}
```

2. **Site 1 — run_pr_create_phase**: after `out=$("$SCRIPT_DIR/create-pr.sh" ... 2>&1)` and `rc=$?`, before `[ "$rc" -eq 0 ] || exit_stall 9b`, add:
```bash
if [ "$rc" -ne 0 ] && is_transient_net_signature "$out"; then
    exit_transient_net "create-pr: $out"
fi
```

3. **Site 2 — run_ci_phase, merge branch** (`version_already_published|policy_denied|admin_failed|error` case): before the `state_set_many BAIL_REASON ...` line that sets stall on error/admin_failed, add:
```bash
if [[ "$merge_result" == "error" || "$merge_result" == "admin_failed" ]] && is_transient_net_signature "$error_text"; then
    exit_transient_net "merge-pr: $error_text"
fi
```

4. **Site 3 — run_ci_phase, bail branch**: before `needs_user_bail_reason "$bail_reason"` check, add:
```bash
if is_transient_net_signature "$bail_reason"; then
    exit_transient_net "ci-wait: $bail_reason"
fi
```

5. **Site 4 — run_rebase_rebump**: after the `rebase_out=... rebase_rc=$?` line for the FIRST rebase call (the non-push one), on the `elif [ "$rebase_rc" -ne 0 ]` branch, add:
```bash
elif [ "$rebase_rc" -ne 0 ]; then
    if is_transient_net_signature "$rebase_out"; then
        exit_transient_net "rebase: $rebase_out"
    fi
    exit_stall "..."
fi
```

**File**: `skills/implement/SKILL.md`

Add after the Exit 5 paragraph in Step 8+:

> **Exit 6**: transient network failure. Read `BAIL_REASON` for telemetry. Read `PHASE` from `ship-pr-state.sh`. Maintain a per-phase retry counter at `$IMPLEMENT_TMPDIR/ship-pr-net-retries-$PHASE.count` (initialize to 0 if missing; increment on each Exit 6 for this `PHASE`). If the count is ≤ 3: foreground `sleep 30` (NOT `ScheduleWakeup` — see NEVER #9), then re-invoke `ship-pr.sh` with the same arguments plus `--resume-phase $PHASE`. On the 4th transient failure for the same phase, treat as Exit 4: set `STALL_TRACKING=true` in the state file via a key-based rewrite, and continue to Step 16. Do NOT end the turn on Exit 6; the retry is part of the same orchestrator turn.

**File**: `scripts/ship-pr.md`

Add to Exit Codes section:
> - `6` — transient network failure. Orchestrator retries the same `PHASE` after a short sleep. `BAIL_REASON` carries the underlying network-signature; `STALL_TRACKING=false` distinguishes it from `exit 4`.

**File**: `scripts/test-ship-pr.sh`

Add 6 new test cases (4 positive, 2 negative) using custom stubs per call site per the issue spec.

## Testing strategy
- `make test-ship-pr` covers Part C's new cases.
- `make test-ci-wait` covers Part A's new harness.
- `/relevant-checks` after all edits.

## Edge cases
- `iter_delta` computation uses `date +%s` which is available on macOS and Linux.
- The transient classifier does NOT touch `exit_stall` calls for local-only failures (classify-bump, apply-bump, postbump-state-corrupt, branch-mismatch, unknown merge_result).
- If `ship-pr.sh` exits 6 but `STALL_TRACKING` was previously `true` (shouldn't happen — transient exits always set it false), the orchestrator counter logic reads the live state file and acts accordingly.

## Files to modify
- `scripts/ci-wait.sh`
- `scripts/ship-pr.sh`
- `skills/implement/SKILL.md`
- `scripts/ship-pr.md`
- `scripts/test-ship-pr.sh`
- Makefile (add `test-ci-wait` target if not present)

## New files
- `scripts/test-ci-wait.sh`
- `scripts/test-ci-wait.md`
