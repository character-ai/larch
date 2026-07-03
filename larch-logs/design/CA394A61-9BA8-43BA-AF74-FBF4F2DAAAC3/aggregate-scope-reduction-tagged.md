### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py
- **Concern**: [SCOPE-REDUCTION] Append-mode batch registry has no producer. Scenario: Omit run_log_batch.py, docs/run-log-batches.md, and test_run_logs.py registry work unless the telemetry writer calls run-log append. The plan writes checks-digest-sizes.tsv via direct locked append in checks_run_relevant.py, so the batch entry is a second schema declaration with no runtime consumer and must stay synchronized manually.
- **Proposed resolution**: Drop the checks-digest-sizes batch registration and related docs/tests from this change, or switch the writer to run-log append --batch checks-digest-sizes and delete the direct locked-TSV path.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:43-81
- **Concern**: [SCOPE-REDUCTION] checks-digest-sizes run-log batch registry has no runtime consumer. Scenario: Telemetry is written by direct locked TSV append in checks_run_relevant; run-log commit copies the whole run tree, so the append-mode batch entry plus registry/docs/tests add sync surface with no behavioral gain
- **Proposed resolution**: Omit run_log_batch.py, test_run_logs.py, and docs/run-log-batches.md changes unless a run-log append producer is added in the same PR
