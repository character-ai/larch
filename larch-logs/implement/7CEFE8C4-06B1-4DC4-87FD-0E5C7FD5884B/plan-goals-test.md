## Goal
Implement issue #6385: [IMPLEMENTING] [BUG] Design round Gantt never renders the Gate B apply (gate-b-apply row unwritten).

## Implementation Plan
## Plan

Approach

- Keep the fix minimal.
- In `_gate_b_apply_start_s`, stop requiring vendor rows to have `cols[3] == "design"`.
- Keep the existing guards for row version, row type, field count, duplicate `gate-b-apply` output, parseable times, and overlap with the round window.
- Do not relabel plan-review vendor rows. The approved outline makes that a non-goal.
- Do not change the Gantt renderer or round-window derivation.

Files to modify/create

### UPDATED: python/larch/review/plan_review_loop.py

- Change the vendor-row guard in `_gate_b_apply_start_s`.
- Remove only the `cols[3] != "design"` exclusion.
- Preserve duplicate detection for existing `gate-b-apply` rows.
- Preserve the existing return behavior:
  - `None` when no ledger exists.
  - `None` when no candidate vendor task ends before the round end.
  - `None` when the apply row was already recorded.
  - Latest overlapping vendor `end_s` otherwise.

### UPDATED: python/tests/review/test_plan_review.py

- Update `_write_design_vendor_timing` to accept a `skill: str = "design"` argument, if useful for the regression.
- Add or parameterize a regression that writes plan-review vendor rows with `skill="implement"`.
- Include a `.gate-b-postapply-ready-1` marker and a `round-start-s` file.
- Call `_write_design_round_meta` twice to keep idempotency coverage.
- Assert one `gate-b-apply` row is written.
- Assert the row uses:
  - skill `design` for the synthetic apply row.
  - vendor `claude`.
  - start time equal to the last reviewer or voter `end_s`.
  - end time equal to the frozen round end.
  - output `gate-b-apply-round-1.out`.
- Keep existing design-labeled coverage valid.

Edge cases

- An existing `gate-b-apply` row with the same output basename must still block duplicate writes.
- Vendor rows outside the round window must still be ignored.
- Rows with malformed start or end times must still be ignored.
- Empty, missing, or unreadable ledgers must still return `None`.
- A marker without any usable vendor rows must still avoid recording an apply row.

Failure modes

- Dropping the skill filter could anchor on unrelated vendor rows if a future design ledger mixes unrelated skill rows in the same file. This is acceptable for this fix because the timing ledger is per run and the approved outline rejects broader relabeling.
- If tests only cover `skill="design"` rows, the original bug can recur. The regression must use `skill="implement"` rows.
- If the test asserts only `_gate_b_apply_start_s`, it may miss the actual write path. Prefer exercising `_write_design_round_meta`.

Testing strategy

- Run the focused Python tests:
  - `python3 -m pytest python/tests/review/test_plan_review.py -k 'gate_b_apply or write_design_round_meta_records_gate_b_apply'`
- If time allows, also run the renderer tests that prove existing consumers still render the row:
  - `python3 -m pytest python/tests/report/test_progress_report.py -k 'gate_b_apply'`
- Run relevant Python lint/checks for changed files if available:
  - `python3 python/cli.py checks run-relevant`

## Acceptance

See Testing strategy in plan.

diff_added: 8
diff_deleted: 1
mechanical_churn: false
diff_lines: 9

## Test plan
(no test plan section in plan-file)
