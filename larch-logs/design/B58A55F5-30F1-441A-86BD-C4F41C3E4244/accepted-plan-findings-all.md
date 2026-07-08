### FINDING_1: Fallback rows are still dropped under cap pressure
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Label-only changes do not prevent late phase2/phase3 fallback rows from being truncated at `PROGRESS_GANTT_ROW_CAP`, so the reproduced omission can remain even after the label fix and small tests will not cover the cap-drop path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Also mark phase2/phase3 fallback rows in _progress_vendor_rows (normalized basename differs from raw) and reserve them in _cap_gantt_rows_reserving_apply alongside apply rows, or an equivalent minimal cap hook tied to the same fallback predicate.
  - From Cursor-Innovation: Build the dual-row test with at least PROGRESS_GANTT_ROW_CAP other vendor rows plus codex/validity-vote failure and cursor phase2 success; assert the fallback row survives capping and renders with the fallback suffix.
  - From Cursor-Pragmatic: Extend the existing apply-reservation helper (or equivalent minimal flag in _progress_vendor_rows) to also preserve rows whose basename normalizes to a phase2/phase3 fallback of a primary attempt, and add a cap-pressure regression test modeled on the C9457B68 ledger shape.
  - From Cursor-Requirements: Extend _cap_gantt_rows_reserving_apply (same pattern as #5264 apply reservation) to keep rows whose normalized basename differs from raw basename, or add an explicit plan step to reserve fallback rows before start-sorted truncation. Add a cap-bound regression test modeled on test_progress_vendor_rows_reserve_coder_apply_under_cap.
  - From Cursor-Arch: Add a cap-saturation case using codex-validity-vote-output-phase2.txt (the run-log basename) with more than 25 ledger rows and assert the phase2 fallback row survives truncation with a (via fallback) label.
  - From Cursor-Pragmatic: Add the codex-output-phase2 + vendor=cursor primary/fallback pair to _progress_vendor_rows coverage, and assert the distinct reconciled label plus survival under cap when the round is row-heavy.
  - From Cursor-Requirements: Add a test that pre-fills PROGRESS_GANTT_ROW_CAP-1 early reviewer rows, then asserts both the failed primary and the phase2 fallback survive (this test requires the cap reservation change above).


### FINDING_2: [OUT_OF_SCOPE] Annotation grammar divergence for fallback labels
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: This is an out-of-scope consistency note: the chart labels will use `(via fallback)` while Top-reviewers #5838 uses `(via <Tool>)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Unify only if operators want one annotation grammar everywhere.


### FINDING_3: Fallback labels can credit the wrong executor, and raw-basename precedence is untested
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Innovation
- **Severity**: major
- **Concern**: When a phase2 fallback basename differs from the manifest basename, the displayed label can collapse to the nominal tool/path instead of crediting the executor, and the planned tests do not prove that raw-basename matches still win over normalized fallback candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use voter-slot ledger rows (codex-validity-vote-output.txt failed primary plus codex-validity-vote-output-phase2.txt with vendor=cursor and kind cursor-phase2-voter-1) and assert vendor-aware fallback labeling when basename prefix disagrees with executing vendor.
  - From Cursor-Pragmatic: When a fallback basename is detected, reconcile the displayed tool with the ledger vendor (or reuse the existing _fallback_reconciled_manifest_label (via Tool) pattern from Top reviewers) so cross-vendor fallbacks render as cursor/validity-vote (via fallback) or codex/validity-vote (via Cursor), not codex/validity-vote (via fallback).
  - From Codex-Innovation: Add one focused case in test_progress_label_fallbacks_and_manifest_precedence that uses a -phase2 output with both raw and normalized candidates and asserts the exact raw basename wins; keep the existing normalized-fallback case beside it.


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:999-1064
- **Concern**: [SCOPE-REDUCTION] Label-only _derive_progress_label change cannot satisfy issue scope when PROGRESS_GANTT_ROW_CAP is saturated. Scenario: C9457B68 Round 1 chart has exactly 25 rows; timing-report.json records cursor-phase2-voter-1 at 89s but the Gantt omits it while keeping the 10s codex/validity-vote failure. _cap_gantt_rows_reserving_apply keeps */apply and earliest non-apply rows, so the later phase2 success is dropped. Plan edge cases explicitly preserve unchanged cap policy, so the repro stays broken after label suffix work alone.
- **Proposed resolution**: Reserve phase2/phase3 fallback ledger rows in _cap_gantt_rows_reserving_apply (same pattern as */apply): mark rows where normalized basename differs from raw basename and keep them out of the start-sorted drop set; add a cap-saturated regression test with >25 rows including a late phase2 voter success.

### FINDING_1: Test the non-complete primary row in C9457B68-shaped vendor-row cases
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned dual-row and cap-pressure tests model a failed primary row, but they keep `_progress_vendor_rows` on its default `require_complete_status=True`. Production Gantt rendering explicitly uses `require_complete_status=False`, so non-complete primaries like the 10s `codex/validity-vote` attempt are included there. As written, the tests can pass while never exercising the production filter path that keeps the failed primary visible alongside the late phase2 success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `In the dual-row and cap-pressure cases, call _progress_vendor_rows(..., require_complete_status=False) and write the failed primary with a non-complete status (e.g. failed).`
  - From Cursor-Innovation: `In the cap-pressure regression, pass require_complete_status=False (and give the failed primary a non-complete status), or document that only the phase2 reservation is under test and keep the primary status=complete without calling the scenario C9457B68-shaped.`
  - From Cursor-Pragmatic: `In planned vendor-row tests, pass require_complete_status=False on every C9457B68-shaped case (dual-row and cap-pressure). Keep failed-primary ledger rows on a non-complete status such as failed. Optionally add one assertion that the failed primary label lacks " (via fallback)" while the phase2 row keeps it.`


### FINDING_2: Pin cap-pressure timestamps so the failed primary is not truncated away
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The cap-pressure fixture’s start-order assumptions can drop the failed primary while preserving the reserved phase2 fallback row. With CAP-1 filler rows plus a reserved phase2 fallback, start-sorted truncation keeps the earliest 25-len(reserved) non-reserved rows; if the failed primary is appended after the filler block, it becomes the latest non-reserved row and is dropped, which contradicts the planned assertion that both rows survive and mis-models the reported C9457B68 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Pin timestamps explicitly: phase2 fallback starts after the filler block; failed primary starts early enough (before the filler tail) that it is not the last non-reserved row when only fallback rows are reserved.`


### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/progress_report.py:561-568
- **Concern**: [SCOPE-REDUCTION] Plain retry rows are treated as vendor fallbacks. Scenario: The plan uses norm_base != raw_base as the fallback predicate, but _progress_normalize_output_base also strips -retry. Existing timing ledgers contain phase1 retry rows such as cursor-plan-requirements-output-ns-retry.txt; the proposed path would normalize that to cursor-plan-requirements-output-ns.txt, append (via fallback), and reserve it under the cap even though no phase2 or phase3 vendor fallback ran.
- **Proposed resolution**: Use a separate chart fallback predicate that requires a stripped -phase2 or -phase3 suffix. Keep plain -retry and -ns-retry rows on the existing raw-label path, and add a focused regression case for a phase1 retry row with no fallback suffix.


