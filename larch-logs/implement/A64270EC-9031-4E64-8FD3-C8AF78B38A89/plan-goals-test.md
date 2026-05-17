## Goal
Complete #2220 symmetry: write plan-review-tally batch from /design and mirror token-ledger marks beside timing-ledger marks

## Implementation Plan

Goal: complete #2220 symmetry — (A) write plan-review-tally batch from /design's tally-plan-review.sh on the HARD path; (B) mirror token-ledger.sh mark calls beside the four timing-ledger.sh mark calls added by #2220.

### Part A — flush_plan_review_batch in tally-plan-review.sh

**File: skills/design/scripts/tally-plan-review.sh**

1. Add accepted/rejected counters initialized before the `{ ... } > "$tally_file"` block:
   ```bash
   accepted_count=0
   rejected_count=0
   ```
2. Inside the for loop, within the `{ ... } > "$tally_file"` block, increment for `kind=="finding"` blocks:
   - `accepted_count=$((accepted_count + 1))` when `result=="accepted"`
   - `rejected_count=$((rejected_count + 1))` otherwise
3. Add a `flush_plan_review_batch()` function that:
   - Guards on `SESSION_ENV_PATH` being set and the `write-tally.sh` script being executable
   - Reads `IMPL_TMPDIR` from `$SESSION_ENV_PATH` using `$PLUGIN_ROOT/scripts/read-session-env-key.sh --file "$SESSION_ENV_PATH" --key PREV_IMPLEMENT_TMPDIR --default ""`
   - Reads `RUN_ID` from `$IMPL_TMPDIR/session-id` (tr -d '\r\n')
   - Guards on both being non-empty
   - Composes a body file under `$DESIGN_TMPDIR` combining tally_file content
   - Calls `"$PLUGIN_ROOT/scripts/write-tally.sh" --log-root "$IMPL_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --phase plan-review --mode hard --rounds 1 --accepted "$accepted_count" --rejected "$rejected_count" --body-file <body-file> || { warning_flush; true; }`
   - On failure, appends to `$IMPL_TMPDIR/execution-issues.md` via `append-execution-issue.sh`
4. Call `flush_plan_review_batch` after the `} > "$tally_file"` block (both the normal-vote path and the 0-eligible-count path if SESSION_ENV_PATH set)

**File: skills/design/scripts/tally-plan-review.md**

Update: add note that on HARD-path HARD-mode runs (SESSION_ENV_PATH provided), a `plan-review-tally` larch-log batch is written to the parent /implement tmpdir.

**File: skills/design/scripts/test-tally-plan-review.sh**

Add a regression test that verifies the `plan-review-tally` larch-log batch file is written when a mock PREV_IMPLEMENT_TMPDIR and session-env-path are provided.

### Part B — mirror token-ledger.sh mark calls

**File: skills/implement/scripts/step2-implement.sh** (line ~202)

Add immediately before the existing timing-ledger.sh mark:
```bash
"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true
"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 2 — implementation" || true
```

**File: skills/review-and-fix/scripts/review-and-fix.sh** (line ~574-576)

Add immediately before the existing timing-ledger.sh mark (inside the `round_num_dec == 1` gate):
```bash
if (( round_num_dec == 1 )); then
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 5 — code review" || true
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 5 — code review" || true
fi
```

**File: scripts/run-relevant-checks-captured.sh** (lines ~117-121)

Add token-ledger mark beside each timing mark in the case statement:
```bash
case "$SITE" in
    step3)
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/token-ledger.sh" mark "Step 3 — checks first pass" || true
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/timing-ledger.sh" mark "Step 3 — checks first pass" || true
        ;;
    step6)
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/token-ledger.sh" mark "Step 6 — checks second pass" || true
        IMPLEMENT_TMPDIR="$TMPDIR_CANONICAL" "$SCRIPT_DIR/timing-ledger.sh" mark "Step 6 — checks second pass" || true
        ;;
esac
```

### Sibling .md updates

- `skills/design/scripts/tally-plan-review.md` — add plan-review-tally flush contract note
- `skills/implement/scripts/step2-implement.md` — note token-ledger mark added
- `skills/review-and-fix/scripts/review-and-fix.md` — note token-ledger mark added alongside timing mark
- `scripts/run-relevant-checks-captured.md` — note token-ledger marks added at step3/step6 sites


## Test plan

Run `/relevant-checks` after implementation; the pre-commit hook (agent-lint) will validate shell scripts. Test the plan-review-tally regression by running:
```
bash skills/design/scripts/test-tally-plan-review.sh
```
Confirm it passes.
