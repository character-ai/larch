## Goal
Implement issue #6578: [IMPLEMENTING] [BUG] Round reviewer-timing chart omits phase2/phase3 vendor-fallback runs.

## Implementation Plan
## Plan

## Approach

Fix the Round reviewer-timing Gantt so phase2/phase3 vendor-fallback ledger rows survive row capping and render with correct, distinct labels. The C9457B68 repro fails for two reasons: late fallback rows are dropped by start-sorted truncation at `PROGRESS_GANTT_ROW_CAP`, and labels can credit the nominal tool instead of the executing vendor.

Keep timing ledger format, Top-reviewers `_fallback_label_remap` / `(via <Tool>)` behavior, CI skipping, and apply-row reservation unchanged.

### Chart fallback predicate (separate from normalization)

Do **not** use `norm_base != raw_base` as the chart fallback predicate. `_progress_normalize_output_base` also strips plain `-retry` (and chained `-retry`), which would misclassify phase1 retry rows such as `cursor-plan-requirements-output-ns-retry.txt` as vendor fallbacks.

Add a small helper (e.g. `_is_chart_vendor_fallback_output(base: str) -> bool`) that returns true only when the basename stem ends with `-phase2` or `-phase3` before the `.txt` extension. Use this predicate exclusively for:

- chart `(via fallback)` suffix eligibility,
- cross-vendor label derivation on fallback rows, and
- cap reservation of fallback rows.

Keep `_progress_normalize_output_base` for manifest lookup and normalized basename derivation; it remains the normalization path, not the fallback detector.

Plain `-retry` / `-ns-retry` rows stay on the existing raw-label path: no `(via fallback)` suffix and no fallback cap reservation.

### Label derivation (`_derive_progress_label`)

Change `_derive_progress_label` only for non-apply rows (apply kinds still return before basename handling).

1. Compute `raw_base = Path(output).name`.
2. Treat a row as a chart fallback row when `_is_chart_vendor_fallback_output(raw_base)` is true.
3. Resolve manifest labels with raw-first precedence: lookup `raw_base` in `label_map`, then `_progress_normalize_output_base(raw_base)`.
4. When no manifest label matches and the row is a chart fallback row, derive from `_progress_normalize_output_base(raw_base)`, not the raw `phase2`/`phase3` name.
5. For chart fallback rows where the resolved base label implies a nominal tool that differs from the ledger `vendor`, reconcile display with the executing vendor using the same slot/tool split as `_fallback_reconciled_manifest_label` / `_manifest_fallback_base_label` (e.g. failed `codex-validity-vote-output.txt` primary plus `codex-validity-vote-output-phase2.txt` with `vendor=cursor` renders `cursor/validity-vote`, not `codex/validity-vote`).
6. Append ` (via fallback)` only when step 2 detected a chart fallback row and a label was actually selected or derived (not for exact raw-basename manifest hits, not for apply rows, not for plain `-retry` rows).

Out-of-scope note: chart fallback annotation stays `(via fallback)`; Top-reviewers keeps `(via <Tool>)` unless a separate unification issue is filed.

### Cap reservation (`_cap_gantt_rows_reserving_apply` + `_progress_vendor_rows`)

Extend the existing #5264 apply-reservation pattern so phase2/phase3 fallback rows are not silently truncated.

1. In `_progress_vendor_rows`, when building each row tuple, set a fallback flag with `_is_chart_vendor_fallback_output(Path(output).name)` (same predicate as labeling).
2. Extend `_cap_gantt_rows_reserving_apply` (minimal in-place change; no rename required) to reserve both:
   - apply rows (`kind in _CODER_APPLY_TASK_KINDS`, unchanged), and
   - chart fallback rows (`-phase2` / `-phase3` suffix only).
3. Fill the remaining budget with earliest-starting non-reserved rows, then return kept rows in chronological order. Preserve current behavior when neither apply nor fallback rows are present.

This directly fixes the C9457B68 case where the 89s `cursor-phase2-voter-1` row starts after 25 earlier reviewer rows and was dropped while the 10s failed primary survived.

## Files to modify/create

### UPDATED: python/larch/report/progress_report.py

**`_is_chart_vendor_fallback_output` (new)**

- Return true only when the basename stem ends with `-phase2` or `-phase3`.
- Do not treat plain `-retry`, `-ns-retry`, or other normalization-only suffixes as chart fallbacks.

**`_derive_progress_label`**

- Add raw-then-normalized manifest lookup.
- Use `_is_chart_vendor_fallback_output` for fallback detection (not `norm_base != raw_base`).
- Derive from normalized basename on chart fallback rows when manifest lookup misses.
- Reconcile cross-vendor fallback labels with ledger `vendor` using existing Top-reviewers reconciliation helpers where applicable.
- Append ` (via fallback)` only for chart fallback rows with a resolved label.

**`_progress_vendor_rows`**

- Pass a fallback flag into the internal row tuple (alongside the existing apply flag) using `_is_chart_vendor_fallback_output`.

**`_cap_gantt_rows_reserving_apply`**

- Reserve chart fallback rows alongside apply rows before start-sorted truncation.
- Update docstring to document both reserved categories (#5264 apply + phase2/phase3 vendor fallback only).

Planned behavior:

- `cursor-specialist-validity-vote-output-phase2.txt` with a manifest label keyed to `cursor-specialist-validity-vote-output.txt` renders as `cursor/validity-vote (via fallback)` when appropriate.
- `codex-validity-vote-output-phase2.txt` with `vendor=cursor` and `kind=cursor-phase2-voter-1` renders as `cursor/validity-vote (via fallback)`, not `codex/validity-vote (via fallback)`.
- `cursor-plan-requirements-output-ns-retry.txt` keeps the existing raw-label path: no `(via fallback)` suffix and no fallback cap reservation.
- Exact raw manifest basename still wins over normalized fallback candidates.
- Normal primary rows, CI skipping, apply priority, and non-fallback cap behavior stay unchanged.

### UPDATED: python/tests/report/test_progress_report.py

Add focused tests near existing progress label and Gantt row tests (`test_progress_label_fallbacks_and_manifest_precedence`, `test_progress_vendor_rows_reserve_coder_apply_under_cap`).

**`_is_chart_vendor_fallback_output` / `_derive_progress_label` coverage**

- Extend `test_progress_label_fallbacks_and_manifest_precedence`:
  - Raw basename manifest hit wins over normalized candidate for the same logical slot.
  - `-phase2` output maps through normalized manifest label and adds ` (via fallback)`.
  - Normalized fallback derivation when no manifest label exists.
- Add cross-vendor fallback case: `codex-validity-vote-output-phase2.txt` with `vendor=cursor`, `kind=cursor-phase2-voter-1` asserts `cursor/validity-vote (via fallback)`.
- Add phase1 retry regression: `cursor-plan-requirements-output-ns-retry.txt` (or equivalent plain `-retry` basename) asserts no ` (via fallback)` suffix and follows the existing raw-label path.
- Keep existing apply-task priority assertions unchanged.

**`_progress_vendor_rows` coverage**

- Dual-row window (production filter path):
  - Call `_progress_vendor_rows(..., require_complete_status=False)` — matching `_render_phase_gantt`.
  - Failed primary `codex-validity-vote-output.txt` with `status=failed` (or another non-complete status), short duration (~10s).
  - Successful `codex-validity-vote-output-phase2.txt` with `vendor=cursor`, long duration (~89s).
  - Assert both rows appear with distinct labels; failed primary label lacks ` (via fallback)`; phase2 row keeps ` (via fallback)`.
- Cap-pressure regression modeled on `test_progress_vendor_rows_reserve_coder_apply_under_cap`:
  - Call `_progress_vendor_rows(..., require_complete_status=False)`.
  - Pre-fill `PROGRESS_GANTT_ROW_CAP - 2` early reviewer filler rows with monotonically increasing start times in the middle of the window.
  - Pin timestamps explicitly:
    - Failed primary starts early (before the filler tail) so it is not the latest non-reserved row when only fallback rows are reserved.
    - Phase2 fallback success starts after the filler block (late, C9457B68-shaped ~89s success).
  - Failed primary uses `status=failed`; phase2 row uses `status=complete`.
  - Assert both survive truncation, fallback row keeps ` (via fallback)`, failed primary lacks the suffix, and total row count stays at `PROGRESS_GANTT_ROW_CAP`.

## Edge cases

- Exact raw manifest labels still win; normalized lookup is fallback only.
- Only `-phase2` / `-phase3` suffixes trigger chart fallback handling; plain `-retry` and `-ns-retry` do not.
- Rows without a recognizable reviewer basename still use existing unknown/vendor/kind logic; append ` (via fallback)` only when the chart fallback predicate matched and a label was resolved.
- Apply rows (`codex/apply`, `cursor/apply`, `gate-b/apply`) never receive the fallback suffix.
- When cap pressure exceeds reserved apply + fallback rows, later non-reserved rows drop first; reserved fallback rows must not be sacrificed for earlier filler rows.
- Cap-pressure fixtures must pin start times so the failed primary is not the last non-reserved row dropped when only phase2/phase3 rows are reserved.
- Top-reviewers `(via <Tool>)` grammar remains intentionally separate from chart `(via fallback)` unless unified in a follow-up.

## Failure modes

- Label-only changes without cap reservation leave the C9457B68 omission intact under saturated rounds.
- Using `norm_base != raw_base` as the fallback predicate mislabels and over-reserves plain retry rows.
- Normalizing after `_progress_derived_label` can still show `unknown/...phase2` labels.
- Applying the suffix before special-kind handling can corrupt apply rows.
- Applying the suffix to primary rows overstates fallback use.
- Reserving fallback rows without vendor reconciliation can show `codex/... (via fallback)` for cursor-executed phase2 voters.
- Reserving fallback rows but not passing the flag from `_progress_vendor_rows` leaves truncation behavior unchanged.
- Vendor-row tests that keep `require_complete_status=True` can pass without exercising the production Gantt filter that includes failed primaries.

## Testing strategy

Run focused Python tests first:

```bash
python3 -m pytest python/tests/report/test_progress_report.py -q -k 'progress_label or progress_vendor_rows or chart_vendor_fallback'
```

Then run changed-file relevant checks if available:

python3 python/cli.py checks run-relevant

If time permits, run the full report test file:

python3 -m pytest python/tests/report/test_progress_report.py -q

## Difficulty

Localized to one module, but it touches workflow report surfaces, cap policy, cross-vendor attribution, and a suffix-specific fallback predicate. A regression can still hide fallback cost, mis-credit vendors, or mis-tag retry rows, so classify as moderate.

## Acceptance

Run focused Python tests first:

```bash
python3 -m pytest python/tests/report/test_progress_report.py -q -k 'progress_label or progress_vendor_rows or chart_vendor_fallback'
```

Then run changed-file relevant checks if available:

python3 python/cli.py checks run-relevant

If time permits, run the full report test file:

python3 -m pytest python/tests/report/test_progress_report.py -q

diff_added: 128
diff_deleted: 14
mechanical_churn: false
diff_lines: 142

## Test plan
(no test plan section in plan-file)
