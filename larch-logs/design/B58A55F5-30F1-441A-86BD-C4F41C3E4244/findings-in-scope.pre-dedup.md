### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py
- **Concern**: C9457B68 cap and dual-row tests must use require_complete_status=False and non-complete status on the failed primary. Scenario: _render_phase_gantt passes require_complete_status=False (progress_report.py:709) so failed vendor rows like the 10s codex/validity-vote attempt render; _progress_vendor_rows defaults to True and skips non-complete rows. Planned tests call _progress_vendor_rows without overriding the flag and _write_vendor_timing defaults status=complete, so tests can pass while never exercising the production filter path for the failed primary.
- **Proposed resolution**: In the dual-row and cap-pressure cases, call _progress_vendor_rows(..., require_complete_status=False) and write the failed primary with a non-complete status (e.g. failed).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_progress_report.py
- **Concern**: Cap-pressure fixture must pin start times so the failed primary is not dropped after reserving only the phase2 row. Scenario: With CAP-1 filler rows plus a reserved phase2 fallback, start-sorted truncation keeps the earliest 25-len(reserved) non-reserved rows. If the failed primary is appended after 24 fillers it has the latest start among non-reserved rows and is dropped while phase2 survives, contradicting the planned assertion that both survive and mis-modeling C9457B68 where the 10s failure remains and the late phase2 row is omitted.
- **Proposed resolution**: Pin timestamps explicitly: phase2 fallback starts after the filler block; failed primary starts early enough (before the filler tail) that it is not the last non-reserved row when only fallback rows are reserved.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:461-481
- **Concern**: [SCOPE-REDUCTION] Step 5 routes Gantt cross-vendor reconciliation through `_fallback_reconciled_manifest_label` / `_manifest_fallback_base_label`, which emit Top-reviewers human titles (e.g. `Cursor Arch`) or `(via <Tool>)` strings, not the `tool/slot` labels `_progress_label_map_from_manifests` stores (`codex/cursor-plan-arch`).. Scenario: On a plan-review phase2 row whose normalized manifest label is `codex/cursor-plan-arch` but ledger `vendor=cursor`, calling those helpers can render a human title or the wrong grammar instead of `cursor/cursor-plan-arch (via fallback)`, regressing design Gantt labels while implement voter rows (derived `codex/validity-vote`) happen to look fine.
- **Proposed resolution**: Reconcile only `tool/slot` labels: when `norm_base != raw_base` and `vendor` differs from the label's leading tool token, replace that token with `vendor`, then append ` (via fallback)`. Do not call `_manifest_fallback_base_label` or `_fallback_reconciled_manifest_label` from `_derive_progress_label`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py:919-950
- **Concern**: C9457B68-shaped cap regression calls `_progress_vendor_rows` with default `require_complete_status=True`, but production Gantt uses `require_complete_status=False` from `_render_phase_gantt`.. Scenario: A cap test that marks the short primary row `status=signal`/`failed` (matching the visible 10s `codex/validity-vote` failure) will filter that row out, so the test never exercises the dual-row window the issue describes and can pass while the chart path still misbehaves for non-complete primaries paired with late phase2 successes.
- **Proposed resolution**: In the cap-pressure regression, pass `require_complete_status=False` (and give the failed primary a non-complete status), or document that only the phase2 reservation is under test and keep the primary `status=complete` without calling the scenario C9457B68-shaped.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_progress_report.py:919-1003
- **Concern**: Planned cap-pressure and dual-row tests omit `require_complete_status=False` even though production Gantt uses it. Scenario: `_render_phase_gantt` calls `_progress_vendor_rows(..., require_complete_status=False)` so failed primaries like C9457B68's 10s `codex/validity-vote` row are included. Planned tests call `_progress_vendor_rows` with the default `require_complete_status=True`, which drops non-`complete`/`OK` rows. With the planned `PROGRESS_GANTT_ROW_CAP - 1` prefill plus failed primary plus late phase2 success, only 24 complete fillers and one complete phase2 remain (25 rows), so no truncation occurs and the cap-reservation regression can pass without the fix. The dual-row case also cannot assert both failed primary and phase2 labels appear.
- **Proposed resolution**: In planned vendor-row tests, pass `require_complete_status=False` on every C9457B68-shaped case (dual-row and cap-pressure). Keep failed-primary ledger rows on a non-complete status such as `failed`. Optionally add one assertion that the failed primary label lacks ` (via fallback)` while the phase2 row keeps it.



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:561-568
- **Concern**: [SCOPE-REDUCTION] Plain retry rows are treated as vendor fallbacks. Scenario: The plan uses norm_base != raw_base as the fallback predicate, but _progress_normalize_output_base also strips -retry. Existing timing ledgers contain phase1 retry rows such as cursor-plan-requirements-output-ns-retry.txt; the proposed path would normalize that to cursor-plan-requirements-output-ns.txt, append (via fallback), and reserve it under the cap even though no phase2 or phase3 vendor fallback ran.
- **Proposed resolution**: Use a separate chart fallback predicate that requires a stripped -phase2 or -phase3 suffix. Keep plain -retry and -ns-retry rows on the existing raw-label path, and add a focused regression case for a phase1 retry row with no fallback suffix.



