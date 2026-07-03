### OOS_1: [OUT_OF_SCOPE] gate-b-apply is not added to _CODER_APPLY_TASK_KINDS so _cap_gantt_rows_reserving_apply may drop the late-starting Gate B bar when a round already has PROGRESS_GANTT_ROW_CAP (25) vendor rows
- **Description**: [OUT_OF_SCOPE] gate-b-apply is not added to _CODER_APPLY_TASK_KINDS so _cap_gantt_rows_reserving_apply may drop the late-starting Gate B bar when a round already has PROGRESS_GANTT_ROW_CAP (25) vendor rows. Scenario: Same failure mode as issue #5264 for */apply lanes: the new bar starts after reviewers/voters and can be truncated, restoring an unlabeled tail on heavy panels
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:890-960
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Idempotence keys gate-b-apply rows only by round number basename while Step 3 re-entry clears .gate-b-postapply-ready-* but not prior ledger rows
- **Description**: [OUT_OF_SCOPE] Idempotence keys gate-b-apply rows only by round number basename while Step 3 re-entry clears .gate-b-postapply-ready-* but not prior ledger rows. Scenario: Gate C re-run review panel can rerun Gate B for the same round: the marker is recreated but gate-b-apply-round-N.out already exists, so a second apply span gets no bar and the gap returns
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:460-461
- **Phase**: design



### OOS_3: gate-b-apply is not reserved under PROGRESS_GANTT_ROW_CAP
- **Description**: gate-b-apply is not reserved under PROGRESS_GANTT_ROW_CAP. Scenario: Late-starting gate-b-apply rows follow the same cap pattern as */apply before #5264: _cap_gantt_rows_reserving_apply only protects _CODER_APPLY_TASK_KINDS (progress_report.py:890-893). A full panel near the cap could drop gate-b/apply and recreate the unlabeled tail. Typical design rounds are ~15 vendor rows, so this is edge-case only. Plan explicitly excludes cap changes.
- **Reviewer**: Cursor-dyn-Timing Ledger Integrity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/report/progress_report.py:886-960, python/tests/report/test_progress_report.py:919-949
- **Phase**: design



