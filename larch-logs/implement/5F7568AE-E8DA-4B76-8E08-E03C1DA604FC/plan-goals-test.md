## Goal
Add SCOUT_STATUS to review-summary.json, commit final-summary.md pre-merge, and aggregate rejected-findings.md with full detail

## Implementation Plan
## Objective
Fix three observability regressions in the committed run-log:
(A) SCOUT_STATUS and panel counts missing from review-summary.json
(B) final-summary.md not committed to run-log for successful merges (post-merge sentinel suppresses larch-log commit)
(C) Run-root rejected-findings.md still uses bare-ledger format instead of full-detail format


### Part A — Add scout_status and panel counts to review-summary.json

Files to modify:
- `skills/review/scripts/emit-tally.sh` — add `--scout-status`, `--dynamic-slots`, `--static-slot-count` flags; include `panel` object in JSON; bump `schema_version` to 2
- `skills/review/scripts/review-core.sh` — pass `scout_status`, `dynamic_slots`, `static_slot_count` to emit-tally.sh via emit_args
- `skills/review/scripts/emit-tally.md` — update docs for new flags
- `skills/review/scripts/test-dispatch-panel.sh` — add 3 regression tests asserting `review-summary.json` contains correct `panel.scout_status`, `panel.dynamic_slot_count`

#### emit-tally.sh changes:
1. Add flags: `--scout-status STR`, `--dynamic-slots N`, `--static-slot-count N` (all default to `na`/`0`)
2. Change `schema_version: 1` to `schema_version: 2` in the jq output
3. Add `panel` object to jq output:
   ```json
   "panel": {
     "scout_status": $scout_status,
     "static_slot_count": $static_slot_count,
     "dynamic_slot_count": $dynamic_slots,
     "total_slot_count": ($static_slot_count + $dynamic_slots | floor)
   }
   ```

#### review-core.sh changes:
Add to emit_args (lines 503-512):
```bash
emit_args+=(--scout-status "$scout_status")
emit_args+=(--dynamic-slots "$dynamic_slots")
emit_args+=(--static-slot-count "$static_slot_count")
```

#### test-dispatch-panel.sh additions (at end of file):
Three new tests using emit-tally.sh directly with different scout_status values to assert the review-summary.json schema_version=2 and panel fields are correct.

### Part B — Write final-summary.md before the post-merge sentinel

The post-merge sentinel (`$IMPLEMENT_TMPDIR/post-merge-sentinel`) is written by `ship-pr.sh` immediately after merge. `larch-log.sh` refuses to commit after this sentinel exists. `write-final-report.sh` is called in Step 17 (after merge), so its larch-log commit is suppressed.

Fix: Add `write-final-report.sh` call to the pre-bump log flush block in Step 7a of `skills/implement/SKILL.md`, BEFORE the `larch-log.sh commit` call. This ensures `final-summary.md` is included in the pre-bump commit that rides inside the PR.

In `skills/implement/SKILL.md`, in the "Pre-bump log flush" section, add before the `larch-log.sh commit` line:
```bash
if [ "${no_logs_commit:-false}" != "true" ]; then
  "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/write-final-report.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" || true
fi
```

Note: The Step 17 call is kept for the stalled/non-merged path (where the pre-merge window was never reached). The Step 18 call remains as the safety-net best-effort.

Trade-off: The pre-merge final-summary.md omits the merge SHA. Acceptable per the issue spec — value is in rounds + findings + counts, not the merge SHA.

Also update `skills/implement/scripts/write-final-report.md` to document the pre-bump timing.

### Part C — Replace bare-ledger run-root rejected-findings.md with full-detail aggregate

`review-and-fix.sh` currently copies the bare-ledger `rejected-findings.md` from the last round to `$IMPLEMENT_TMPDIR/rejected-findings.md`. The fix replaces this with a per-round concatenation of `rejected-findings-full.md` files.

In `skills/review-and-fix/scripts/review-and-fix.sh`, in the section that writes `$IMPLEMENT_TMPDIR/rejected-findings.md` (around lines 788-810), replace the simple copy with a function that:
1. Iterates over all `$IMPLEMENT_TMPDIR/round-N/rejected-findings-full.md` files in round order
2. If any exist and are non-empty: outputs `# Rejected Findings\n\n` then for each round: `## Round N\n\n<content of rejected-findings-full.md>\n\n`
3. Falls back to copying the bare-ledger `$round_dir/rejected-findings.md` when no round has a non-empty `rejected-findings-full.md` (backward compat)

Also update `scripts/compose-review-findings.md` → actually the issue mentions `scripts/compose-review-findings.md` but this file writes JSONL records, not the run-root markdown. The correct file is `review-and-fix.sh` which writes `$IMPLEMENT_TMPDIR/rejected-findings.md`.

Update `skills/review-and-fix/scripts/review-and-fix.md` to document the new aggregate behavior.

### Regression Tests

#### Part A (already described above — in test-dispatch-panel.sh)
Tests that emit-tally.sh with `--scout-status na --dynamic-slots 0 --static-slot-count 7` produces:
- `schema_version` = 2
- `panel.scout_status` = `"na"`
- `panel.static_slot_count` = 7
- `panel.dynamic_slot_count` = 0
- `panel.total_slot_count` = 7

#### Part C (extend scripts/test-compose-review-findings.sh)
Wait — the issue references `scripts/test-compose-review-findings.sh` but the run-root rejected-findings.md is written by `review-and-fix.sh`, not `compose-review-findings.sh`. The correct test location is `skills/review-and-fix/scripts/` (existing test harness for review-and-fix.sh).

Add tests to `skills/review-and-fix/scripts/test-review-and-fix.sh` (or a new `scripts/test-rejected-findings-aggregate.sh`) to verify:
1. When round-N/rejected-findings-full.md files exist, run-root rejected-findings.md uses full-detail format with ## Round N headers
2. When no rejected-findings-full.md exists, falls back to bare ledger


## Test plan
- `make lint-bash32` after any .sh edits
- `make lint` (runs pre-commit + agent-lint)
- `/relevant-checks` after all changes committed
