### OOS_1: [OUT_OF_SCOPE] Second locked-TSV append implementation beside tokens._locked_tsv_append
- **Description**: [OUT_OF_SCOPE] Second locked-TSV append implementation beside tokens._locked_tsv_append. Scenario: Plan copies panel-prompt-sizes flock style inline instead of reusing tokens._locked_tsv_append, inviting divergent lock timeout and warning text
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks_run_relevant.py:1018-1037
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry is unused by the direct locked-TSV writer
- **Description**: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry is unused by the direct locked-TSV writer. Scenario: The writer appends `checks-digest-sizes.tsv` in-process and `run-log commit` copies the full run tree, so the batch registry, its tests, and `run-log-batches.md` edits add synchronized surface with no runtime consumer
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py:43-74
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry duplicates the direct locked-TSV writer
- **Description**: [SCOPE-REDUCTION] Append-mode `checks-digest-sizes` batch registry duplicates the direct locked-TSV writer. Scenario: Telemetry is written inside `_write_failure_digest_from_redacted` via locked append, not `run-log append`, so the batch slug plus `test_run_logs.py` registry coverage adds a second schema surface with no runtime consumer and extra sync work
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_batch.py
- **Phase**: design



