## Plan

## Approach

Implement the resolved option: keep the full round window, and add one labeled `gate-b/apply` bar for the Gate B apply, dedup, and postplan span.

Use minimum change:

- Preserve existing `v1 round` and `v1 vendor` row grammar.
- Preserve the round `end_s` stamp point.
- Emit the new bar only when `.gate-b-postapply-ready-{round_num}` exists.
- Reuse `TimingLedger.record_vendor_task`.
- Add a new task kind, `gate-b-apply`.
- Teach the Gantt label derivation to render `gate-b-apply` as `gate-b/apply`.
- Derive the Gate B start as the latest completed design vendor row end inside the round window.
- Use the same frozen `end_s` for the Gate B row and the round row, so no new blank tail appears after the Gate B bar.

## Files to modify/create

### UPDATED: python/larch/report/timing.py

Add `gate-b-apply` to `TIMING_TASK_KINDS_ALLOWED`.

Do not change the `v1 vendor` row shape.

### UPDATED: python/larch/report/progress_report.py

Add a special label case in `_derive_progress_label`:

- `kind == "gate-b-apply"` returns `gate-b/apply`.

Do not change chart window logic, row filtering, row caps, or `/implement` rendering.

### UPDATED: python/larch/review/plan_review_loop.py

Add a small helper near the existing round timing helpers.

Suggested shape:

- Read `round-start-s`.
- Accept the already-frozen `end_s`.
- Scan `timing-ledger.tsv` for `v1 vendor` rows where:
  - skill is `design`.
  - task kind is not `gate-b-apply`.
  - the row overlaps `start_s..end_s`.
- Pick `gate_b_start_s = max(row_end_s)`.
- If no candidate row exists, skip the Gate B bar.
- If `gate_b_start_s >= end_s`, skip the Gate B bar.
- Skip if a prior `gate-b-apply` row with output basename `gate-b-apply-round-{round_num}.out` already exists.
- Append a `v1 vendor` row through `TimingLedger(path=ledger, skill="design").record_vendor_task(...)` with:
  - `vendor="claude"`.
  - `task_kind="gate-b-apply"`.
  - `start_s=gate_b_start_s`.
  - `end_s=end_s`.
  - `output=f"gate-b-apply-round-{round_num}.out"`.
  - `status="complete"`.

Also update `_record_design_round_timing_from_start_file` to accept an optional frozen `end_s`. Keep its current default behavior when no `end_s` is passed.

### UPDATED: python/larch/review/plan_review.py

Update `_write_design_round_meta`:

- Freeze `end_s = int(time.time())` once after the meta write attempt.
- If `.gate-b-postapply-ready-{round_num}` exists, call the new Gate B timing helper before or next to the round timing write.
- Call `_record_design_round_timing_from_start_file(..., end_s=end_s)`.

Keep the existing call sites unchanged. The zero-accepted path will not emit the Gate B bar because the marker is absent.

### UPDATED: python/tests/report/test_timing.py

Add or extend coverage that `TimingLedger.record_vendor_task` accepts `task_kind="gate-b-apply"` with a valid vendor.

Assert the row is written as a normal `v1 vendor` row.

### UPDATED: python/tests/report/test_progress_report.py

Add renderer coverage for a design round with:

- one `v1 round` design window.
- one normal reviewer or voter vendor row.
- one `gate-b-apply` vendor row.

Assert the rendered Gantt includes:

- `### Round 1 reviewer timing`.
- `gate-b/apply`.
- the full declared window.

### UPDATED: python/tests/review/test_plan_review.py

Extend timing coverage around `_write_design_round_meta`:

- Accepted-findings path:
  - create `plan-review/round-1/round-start-s`.
  - create `.gate-b-postapply-ready-1`.
  - add a design vendor row ending before the frozen round end.
  - freeze `plan_review.time.time`.
  - call `_write_design_round_meta`.
  - assert one `gate-b-apply` vendor row exists.
  - assert its start equals the latest prior design vendor end.
  - assert its end equals the frozen round end.
  - assert the round window remains unchanged.
- Idempotence:
  - call `_write_design_round_meta` again.
  - assert there is still only one `gate-b-apply` row for that round.
- Zero-findings path:
  - omit `.gate-b-postapply-ready-1`.
  - assert no `gate-b-apply` row is emitted.

## Edge cases

- **No prior vendor rows**: skip the Gate B bar. This avoids falsely labeling the entire round as Gate B.
- **Duplicate finalization**: detect the round-specific `gate-b-apply` output basename and skip a duplicate row.
- **Clock ties**: if the latest vendor end is equal to or after frozen `end_s`, skip the bar.
- **Signal rows**: include them when deriving the latest subprocess end, because Gate B starts after subprocess completion even when a subprocess failed or signaled.
- **Legacy ledgers**: continue rendering without Gate B rows.

## Failure modes

- If the ledger is missing or unreadable, keep current best-effort behavior and skip only the Gate B bar.
- If the new timing row cannot be appended, follow `TimingLedger.record_vendor_task` behavior. Do not fail the `/design` flow.
- If the label special case is missed, the row may render as `unknown/gate-b-apply`; tests should catch this.

## Testing strategy

Run focused tests:

```bash
python3 -m pytest python/tests/report/test_timing.py python/tests/report/test_progress_report.py python/tests/review/test_plan_review.py
```

Run focused lint for changed Python files if dependencies are available:

```bash
make py-lint
```

If full `make py-lint` is too broad locally, run the repository's relevant checks after implementation:

```bash
python3 python/cli.py checks run-relevant
```

## Non-goals

- Do not move the round-end stamp.
- Do not shrink the Gantt window.
- Do not change `v1 round` or `v1 vendor` grammar.
- Do not touch `/implement` review timing or unrelated charts.
- Do not add a new ledger row type.

## Acceptance

- For a plan-review round with at least one accepted finding, the `### Round N reviewer timing` Gantt renders a labeled `gate-b/apply` bar covering the previously blank trailing span; the declared window start and end are unchanged from current behavior.
- A zero-findings round (no `.gate-b-postapply-ready-{round_num}` marker) emits no `gate-b-apply` row and renders exactly as before.
- `_write_design_round_meta` is idempotent: invoking it twice for the same round yields at most one `gate-b-apply` row.
- The `v1 round` and `v1 vendor` timing-ledger row grammar is unchanged; existing ledger consumers still parse.
- `gate-b-apply` renders as `gate-b/apply` (not `unknown/gate-b-apply`).
- Focused tests pass: `python3 -m pytest python/tests/report/test_timing.py python/tests/report/test_progress_report.py python/tests/review/test_plan_review.py`.
- Relevant checks pass: `python3 python/cli.py checks run-relevant`.

review_status: ok
rounds_completed: 1
diff_lines: 165
