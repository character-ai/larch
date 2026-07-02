### FINDING_1: DEFECT lines must map to `check=contains-pins`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The contains-pins phase writes `DEFECT:` lines with no `===` section header. A header-only phase tracker will attribute those failures to the previous pre-commit or direct-make section, so `check=` can name the wrong hook or target even when `first_location` and `first_error` are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit parser rule: lines matching ^DEFECT: belong to check=contains-pins regardless of the last header; add unit coverage with a log where direct make succeeded and contains-pins failed.


### FINDING_3: Plan cites nonexistent no-validation-phases integration test
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan tells implementers to extend `test_run_relevant_checks_no_validation_phases_when_precommit_unavailable`, but the repo only has `test_run_relevant_checks_deletion_only_without_agent_lint_fails_closed` for `failure_reason=no-validation-phases`. A literal search misses the target, and the mandated digest-on-rc2 path can ship without integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Rename the plan bullet to `test_run_relevant_checks_deletion_only_without_agent_lint_fails_closed`, assert `result.redacted_log_path` when redaction succeeds, then assert `digest_file_path`, digest file mode `0600`, and the `no-validation-phases` envelope includes `DIGEST_FILE=` before `REDACTED_LOG_FILE=`.


