### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:761-868
- **Concern**: DEFECT lines must map to check=contains-pins, not the last section header. Scenario: The contains-pins phase writes DEFECT: lines with no === section header (see _run_contains_pin_phase). A header-only phase tracker will attribute those failures to the previous pre-commit or direct-make section, so check= can name the wrong hook/target even when first_location/first_error are correct.
- **Proposed resolution**: Add an explicit parser rule: lines matching ^DEFECT: belong to check=contains-pins regardless of the last header; add unit coverage with a log where direct make succeeded and contains-pins failed.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py
- **Concern**: Per-field cap missing for first_error inside the global digest byte budget. Scenario: The plan caps total digest bytes and allows multiple check= record groups, but first_error is only described as a bounded line with no per-field byte limit. One verbose traceback or pytest dump can consume the entire CHECKS_FAILURE_DIGEST_MAX_BYTES budget and set digest_truncated=true after the first group, hiding additional failed pre-commit hooks the issue requires surfacing.
- **Proposed resolution**: Define a small CHECKS_FAILURE_DIGEST_FIRST_ERROR_MAX_BYTES (or similar), truncate each first_error before assembling groups, and add a test where one hook emits a huge error yet a second failed hook still appears before digest_truncated=true.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py
- **Concern**: Digest builder must cap and sanitize first_error (and first_location) per field. Scenario: The plan caps total digest UTF-8 bytes and allows Traceback or pre-commit output as first_error, but it does not bound or flatten individual field values. One multiline traceback or huge single line can consume the whole budget so only one check record appears, or embed raw newlines/tabs that break the line-oriented v1 format. That undermines the accepted multi-hook digest goal and makes prompt-side parsing unreliable.
- **Proposed resolution**: In the digest builder spec, add a small per-field UTF-8 byte cap (for example on first_error and first_location), flatten newlines/tabs to spaces before writing, then apply the existing total CHECKS_FAILURE_DIGEST_MAX_BYTES cap across complete record groups. Add unit tests for multiline traceback input and for two check groups still fitting when errors are large. ## Findings ### 1. [correctness] `python/larch/implement/checks_run_relevant.py` — per-field bounds for digest values The plan defines a line-oriented `CHECKS_FAILURE_DIGEST v1` format with `first_error=` and `first_location=` on single lines, plus a total byte cap and multi-check record groups. It does not constrain those field values. Pre-commit, pytest, and make failures often emit multiline tracebacks or very long single lines. Without per-field truncation and newline flattening: - One record can use the entire digest budget, so a second failed hook may never appear despite the multi-check design. - Raw newlines inside `first_error=` corrupt the line-oriented contract the orchestrator is meant to read instead of the full redacted log. **Suggested revision:** Cap `first_error` and `first_location` individually (UTF-8 bytes, valid truncation), normalize whitespace, then enforce the global cap across complete record groups. Extend `python/tests/implement/test_checks.py` with multiline traceback and multi-hook cases. --- **Note on prior ledger:** Round-1 accepted fixes for folded stdout scanning, per-check records, both redacted failure branches, and KV ordering appear in this plan. No new material issues found beyond the field-bounding gap above.



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_checks.py:3562-3596
- **Concern**: Plan cites nonexistent no-validation-phases integration test name. Scenario: The plan tells implementers to extend `test_run_relevant_checks_no_validation_phases_when_precommit_unavailable`, but the repo only has `test_run_relevant_checks_deletion_only_without_agent_lint_fails_closed` for `failure_reason=no-validation-phases`. A literal search misses the target, and the mandated digest-on-rc2 path can ship without integration coverage.
- **Proposed resolution**: Rename the plan bullet to `test_run_relevant_checks_deletion_only_without_agent_lint_fails_closed`, assert `result.redacted_log_path` when redaction succeeds, then assert `digest_file_path`, digest file mode `0600`, and the `no-validation-phases` envelope includes `DIGEST_FILE=` before `REDACTED_LOG_FILE=`. ## Findings ### 1. code-quality — Wrong no-validation-phases test target (`python/tests/implement/test_checks.py:3562-3596`) The plan’s testing section references `test_run_relevant_checks_no_validation_phases_when_precommit_unavailable`, which does not exist in the repo. The only integration test that hits `failure_reason == "no-validation-phases"` today is `test_run_relevant_checks_deletion_only_without_agent_lint_fails_closed`. That test also does not yet assert `redacted_log_path`, which the plan’s new digest assertions depend on. **Suggested revision:** Point the plan at the existing test by name, add a redacted-log assertion when redaction succeeds, then add the planned digest and envelope checks for the rc==2 path. --- Round 1 accepted items (folded-site `DIGEST_FILE` scan, per-check digest records, both `_finish_logged_result` branches) are already reflected in the current plan; no re-raise. Prior rejected/OOS items (KV ordering nit, docs parity, anti-halt harness, `_truncate_utf8_bytes` reuse) are unchanged and not repeated.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:238
- **Concern**: Plan omits the required SECURITY.md update for the new model-facing digest artifact. Scenario: The PR adds a new mode-0600 digest derived from check output and changes orchestrator guidance from reading REDACTED_LOG_FILE first to reading DIGEST_FILE first, but SECURITY.md would still document only the old redacted-log artifact and consumer rule
- **Proposed resolution**: Add SECURITY.md to the firm plan and update the relevant-checks captured logs paragraph to state that failed runs may also write a bounded DIGEST_FILE built only from the redacted log, consumed before REDACTED_LOG_FILE, with raw LOG_FILE still forbidden



