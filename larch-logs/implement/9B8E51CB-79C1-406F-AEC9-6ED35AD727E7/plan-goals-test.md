## Goal
Prevent partial run-log dirs from being committed when manifest.json is missing

## Implementation Plan
## Implementation Plan

### Goal
Fix two defects that allow a partial run-log directory (missing manifest.json) to be committed to larch-logs/implement/.

### Files to Modify
1. `skills/implement/SKILL.md` — Step 0.5 Branch 4 failure handling
2. `scripts/ship-pr.sh` — `run_postmerge_phase`, probe before manifest+commit
3. `scripts/implement-finalize.sh` — `run_teardown`, probe before manifest+commit
4. `scripts/implement-finalize.md` — document the manifest-probe contract
5. `scripts/test-ship-pr.sh` — add missing-manifest test

### Changes

**1. SKILL.md Step 0.5 Branch 4** (line ~618):
Split the failure clause into two distinct cases:
- `LOG_WRITTEN=false` from `larch-log.sh init` → abort (skip to Step 18 with STALL_TRACKING=true)
- `FAILED=true` from `tracking-issue-summary.sh` → continue with deferred (unchanged)

**2. scripts/ship-pr.sh `run_postmerge_phase`** (around line 1052):
Before the manifest+commit block, add:
```bash
local manifest_path_pm
manifest_path_pm="$IMPLEMENT_TMPDIR/larch-logs/implement/$flush_run_id/manifest.json"
if [ ! -f "$manifest_path_pm" ]; then
    fail_file=$(failure_capture_path postmerge)
    "$SCRIPT_DIR/larch-log.sh" init \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement --run-id "$flush_run_id" \
        > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure postmerge "larch-log.sh init (manifest-recovery)" "$rc" "$fail_file" Warnings
    fail_file=$(failure_capture_path postmerge)
    "$SCRIPT_DIR/larch-log.sh" manifest \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement --run-id "$flush_run_id" \
        --field "status=partial" \
        --field "recovery_reason=manifest_lost_mid_run" \
        > "$fail_file" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || record_failure postmerge "larch-log.sh manifest (partial-tag)" "$rc" "$fail_file" Warnings
fi
```

**3. scripts/implement-finalize.sh `run_teardown`** (around line 1492):
Before the manifest+commit block, add similar probe using `larch_flush_run_id` and `warn_line` instead of `record_failure`.

**4. scripts/implement-finalize.md**:
Add a paragraph in the teardown section describing the manifest-presence probe.

**5. scripts/test-ship-pr.sh**:
Add after the existing `postmerge_flush` test: a new test that sets PR_CLOSED=true but does NOT pre-create a manifest.json, then verifies `init` is called (manifest synthesis).

### Testing Strategy
- `/relevant-checks` must pass (pre-commit + agent-lint)
- The new test-ship-pr.sh case verifies manifest synthesis path is exercised

## Test plan
(no test plan section in plan-file)
