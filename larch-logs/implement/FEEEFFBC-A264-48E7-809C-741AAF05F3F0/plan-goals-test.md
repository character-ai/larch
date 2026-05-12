## Goal
Fix teardown-before-Step-18 race in ship-pr.sh and add manifest finalization in implement-finalize.sh teardown.

## Goal
Fix two bugs that together cause session-transcript.jsonl to be missing and manifest.json to stay stuck at status:in-progress after a merged /implement run.

## Implementation Plan

### Bug 1 — Teardown runs too early in ship-pr.sh

`scripts/ship-pr.sh run_postmerge_phase()` (lines 724-739) currently:
1. Reads LARCH_TOKEN_SESSION_ID/LARCH_CLAUDE_SOURCE_FILE from session-env.sh (lines 724-726)
2. Runs token-report.sh (line 727)
3. Writes summary-final.md and upserts tracking-issue-summary (lines 728-735)
4. Calls `implement-finalize.sh teardown` (line 738) — which removes IMPLEMENT_TMPDIR
5. exits 0 (line 739)

The teardown at step 4 removes IMPLEMENT_TMPDIR. When the orchestrator then reaches prompt-side Step 18 (which still runs), the session-env.sh is gone, so LARCH_CLAUDE_SOURCE_FILE is empty, session-transcript.jsonl is never written, and teardown's second invocation fails (state file missing → manifest not finalized).

**Fix**: Remove the early teardown and the duplicate token-report/summary operations from run_postmerge_phase(). Leave only:
```bash
run_postmerge_phase() {
    write_finalize_state
    "$SCRIPT_DIR/implement-finalize.sh" postmerge --state-file ... --final-bail-reason-file ...
    advance_phase "done"
    exit 0
}
```

Steps 3-6 are duplicated by prompt-side Step 18 which does the same work with TMPDIR still available.

### Bug 2 — manifest.json never finalized

`larch-log.sh manifest` subcommand exists but is never called. The manifest stays at `status: in-progress` with `pr_number: null` forever.

**Fix**: In `scripts/implement-finalize.sh run_teardown()`, add a manifest update block BEFORE the `larch-log.sh commit` call, so the finalized manifest is included in the final git commit:

```bash
# Update manifest status before the final commit
if [ -n "$larch_flush_run_id" ] && [ "$repo_unavailable" = "false" ]; then
    if [ "$stall_tracking" = "true" ]; then
        "$SCRIPT_DIR/larch-log.sh" manifest \
            --skill implement --run-id "$larch_flush_run_id" \
            --field "status=stalled" \
            --field "stalled_at_step=$stall_step" \
            2>/dev/null || true
    elif [ -n "$pr_number" ]; then
        "$SCRIPT_DIR/larch-log.sh" manifest \
            --skill implement --run-id "$larch_flush_run_id" \
            --field "status=done" \
            --field "pr_number=$pr_number" \
            2>/dev/null || true
    elif [ "$design_only" = "true" ]; then
        "$SCRIPT_DIR/larch-log.sh" manifest \
            --skill implement --run-id "$larch_flush_run_id" \
            --field "status=done" \
            2>/dev/null || true
    fi
fi
# existing larch-log.sh commit call follows...
```

### Sub-fix — larch-log.sh manifest numeric type handling

The manifest command currently uses `--arg` for all field values, which would set `pr_number` to a JSON string `"1935"` instead of the required JSON number `1935`. Fix: auto-detect values matching JSON number/boolean/null syntax and use `--argjson` for those, `--arg` for everything else.

### Files to modify

1. `scripts/ship-pr.sh` — remove teardown + duplicate operations from run_postmerge_phase
2. `scripts/implement-finalize.sh` — add manifest update before larch-log commit in run_teardown
3. `scripts/larch-log.sh` — fix --argjson vs --arg in manifest subcommand
4. `scripts/ship-pr.md` — update description (remove teardown from ship-pr responsibilities)
5. `scripts/implement-finalize.md` — update teardown description to mention manifest finalization
6. `scripts/larch-log.md` — document auto-JSON-type behavior

## Test plan
- Run /relevant-checks after implementation
- Verify no syntax errors in modified bash scripts (bash -n)
- Verify the removed lines are gone from ship-pr.sh run_postmerge_phase
- Verify manifest update code is present in run_teardown before larch-log commit
- Verify larch-log.sh manifest uses --argjson for numeric values
