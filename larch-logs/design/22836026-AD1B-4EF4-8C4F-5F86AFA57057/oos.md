### FINDING_1: Gate B start scan filters out implement-skill vendor rows
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-dyn-Timing Ledger Integrity
- **Severity**: blocking
- **Concern**: Gate B start derivation is filtering candidate vendor rows by `skill=design`, but the live plan-review timing ledger writes the relevant reviewer, voter, and aggregator rows with `skill=implement`. That mismatch can leave the helper with zero candidates, skip `gate-b-apply`, and preserve the unlabeled trailing tail in accepted-finding rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop the vendor skill == design predicate for this derivation, or match the renderer contract by deriving from rows that overlap the round window and excluding only gate-b-apply. Add the test fixture with reproduction-shaped vendor rows whose skill column is implement.
  - From Cursor-Innovation: Drop the skill=design predicate. Derive gate_b_start_s as max(row_end_s) over all v1 vendor rows overlapping round-start-s..frozen end_s, excluding task_kind gate-b-apply only, matching the rows the Gantt already displays
  - From Codex-Innovation: Derive Gate B start from overlapping vendor rows the same way the Gantt renderer does, or explicitly accept both design and legacy/default implement skill rows for plan-review timing. Add the plan-review test with an implement-skill vendor row.
  - From Cursor-dyn-Timing Ledger Integrity: Drop the skill=design filter. Scan overlapping v1 vendor rows excluding task_kind=gate-b-apply only, matching _progress_vendor_rows which does not filter by skill (progress_report.py:920-961). In test_plan_review.py use skill=implement vendor fixtures aligned with the reproduction ledger, not design-skill rows.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py
- **Concern**: [SCOPE-REDUCTION] Gate B start scan filters vendor rows to skill=design but live plan-review vendor rows use skill=implement. Scenario: On committed design ledgers (e.g. larch-logs/design/F37028B8-64BD-4BB2-96DB-44ADEB6B87B0/timing-ledger.tsv) every Step 3 reviewer/aggregator/voter row is v1 vendor with skill=implement while v1 round rows use skill=design. Filtering gate_b_start candidates to skill=design finds zero overlapping rows, triggers the no-candidate skip, and leaves the Round N Gantt tail unlabeled on the exact reproduction path.
- **Proposed resolution**: Drop the skill=design vendor filter. Derive gate_b_start_s as max(end_s) over v1 vendor rows that overlap round-start-s..frozen end_s, exclude task_kind gate-b-apply, and include signal rows. Match _progress_vendor_rows window overlap (no skill column filter). Update test_plan_review.py and test_progress_report.py fixtures to seed implement-skill vendor rows like production, not design-skill rows.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] gate-b-apply is not added to _CODER_APPLY_TASK_KINDS so _cap_gantt_rows_reserving_apply may drop the late-starting Gate B bar when a round already has PROGRESS_GANTT_ROW_CAP (25) vendor rows
- **Description**: [OUT_OF_SCOPE] gate-b-apply is not added to _CODER_APPLY_TASK_KINDS so _cap_gantt_rows_reserving_apply may drop the late-starting Gate B bar when a round already has PROGRESS_GANTT_ROW_CAP (25) vendor rows. Scenario: Same failure mode as issue #5264 for */apply lanes: the new bar starts after reviewers/voters and can be truncated, restoring an unlabeled tail on heavy panels
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:890-960
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Idempotence keys gate-b-apply rows only by round number basename while Step 3 re-entry clears .gate-b-postapply-ready-* but not prior ledger rows
- **Description**: [OUT_OF_SCOPE] Idempotence keys gate-b-apply rows only by round number basename while Step 3 re-entry clears .gate-b-postapply-ready-* but not prior ledger rows. Scenario: Gate C re-run review panel can rerun Gate B for the same round: the marker is recreated but gate-b-apply-round-N.out already exists, so a second apply span gets no bar and the gap returns
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:460-461
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_3: gate-b-apply is not reserved under PROGRESS_GANTT_ROW_CAP
- **Description**: gate-b-apply is not reserved under PROGRESS_GANTT_ROW_CAP. Scenario: Late-starting gate-b-apply rows follow the same cap pattern as */apply before #5264: _cap_gantt_rows_reserving_apply only protects _CODER_APPLY_TASK_KINDS (progress_report.py:890-893). A full panel near the cap could drop gate-b/apply and recreate the unlabeled tail. Typical design rounds are ~15 vendor rows, so this is edge-case only. Plan explicitly excludes cap changes.
- **Reviewer**: Cursor-dyn-Timing Ledger Integrity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:886-960, python/tests/report/test_progress_report.py:919-949
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

