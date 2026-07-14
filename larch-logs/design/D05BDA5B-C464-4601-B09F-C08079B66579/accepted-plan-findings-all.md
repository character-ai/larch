### FINDING_1: Idempotency parity is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-Parity Auditor, Codex-dyn-Parity Auditor
- **Severity**: major
- **Concern**: The planned idempotency tests do not cover wrapper-visible `RECORDS=0` and unchanged NDJSON batch contents for both sentinel-match and normalized per-section reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a pytest case that performs a successful flush through `run-log append`, removes the sentinel, reruns with the same markdown, and asserts `already-flushed`, `RECORDS=0`, stable batch line count, and empty `execution-issues.md`.
  - From Cursor-Arch: Add `assert second[2] == 0` (and optionally unchanged NDJSON line count) to the preserved idempotency test.
  - From Cursor-Requirements: Extend the preserved idempotent test (or add a sibling case that deletes .execution-issues-flushed.sha after a successful flush) to assert second.records==0, batch line count unchanged, and—when routed through flush_execution_issues_main—RECORDS=0 on stdout
  - From Cursor-dyn-Parity Auditor: Extend idempotent parity via flush_execution_issues_main (capsys FLUSH_STATUS=already-flushed, RECORDS=0) and assert implement/run-id/execution-issues.ndjson line count is unchanged across the second call, matching Bash before==after at lines 196-208.
  - From Cursor-dyn-Parity Auditor: Add flush_execution_issues_main coverage for the batch_matches path with RECORDS=0 and unchanged execution-issues.ndjson line count after rerun, matching Bash lines 228-235.
  - From Codex-dyn-Parity Auditor: Extend both named pytest cases with exact before-and-after NDJSON line counts or contents, including the sentinel-match and normalized-section batch-probe paths.


### FINDING_2: Normal failure coverage must exercise the CLI contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Parity Auditor
- **Severity**: major
- **Concern**: The normal flush-failure test must call `flush_execution_issues_main`, assert exact `FLUSH_STATUS`, `RECORDS`, `APPEND_LOG_FILE`, and exit-code behavior, and match Python `_append_failure` output rather than stale Bash substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the planned failure test to call `flush_execution_issues_main` and assert exact stdout KVs plus exit code `1`, matching the skip-path `main` coverage.
  - From Cursor-Innovation: In the new normal-flush failure case, assert FLUSH_STATUS=failed, RECORDS=0, readable APPEND_LOG_FILE, and issue-log text flush-execution-issues / run-log exited 1; do not port the stale bash substrings
  - From Cursor-Pragmatic: Spell out the normal-flush failure assertion: execution-issues.md contains flush-execution-issues and run-log exited with the injected exit code; do not require stub stderr in the issue log.
  - From Cursor-Requirements: Align the failure bullet with the empty-input bullet: implement via flush_execution_issues_main with a failed run-log subprocess stub and assert exit 1, FLUSH_STATUS=failed, RECORDS=0, readable APPEND_LOG_FILE, and the _append_failure line in execution-issues.md (run-log exited N, not the stale bash strings run-log failed or simulated stderr)
  - From Cursor-dyn-Parity Auditor: Pin the new flush_execution_issues_main failure test to _append_failure output: issue log still contains original content plus - **flush-execution-issues**: run-log exited 1; capsys has FLUSH_STATUS=failed and RECORDS=0; APPEND_LOG_FILE is readable and contains simulated stderr when subprocess.run is stubbed to return rc=1. Do not assert simulated larch-log failure inside execution-issues.md.


### FINDING_3: Focused Make target must run the delegation smoke
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: `make test-flush-execution-issues` currently runs only pytest, so the required Bash delegation smoke is outside the acceptance target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update `test-flush-execution-issues` to run both the focused pytest selection and `bash skills/implement/scripts/test-flush-execution-issues.sh`.
  - From Codex-Innovation: Add the shell smoke to this target after pytest and list Makefile as updated; no shard change is needed
  - From Codex-Pragmatic: Add the rewritten shell smoke to `test-flush-execution-issues` after the focused pytest command
  - From Codex-Requirements: Update the target to run the reduced Bash smoke as well as the focused pytest suite.


### FINDING_8:
- **Reviewer(s)**: Codex-dyn-Parity Auditor
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile:931-932; skills/implement/scripts/flush-execution-issues.sh:6-8
- **Concern**: [SCOPE-REDUCTION] The plan’s “do not change Make targets” leaves the new delegation smoke outside `make test-flush-execution-issues`.. Scenario: The target runs only pytest, so a broken plugin-root selection, wrapper argv boundary, stream passthrough, or delegated exit status can ship while the stated focused Make acceptance target passes.
- **Proposed resolution**: Update the existing focused target minimally to run the rewritten shell delegation smoke after its pytest command.


### FINDING_1: Idempotency parity is underspecified for normalized reruns and sentinel output
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The normalized batch-match rerun bullet has no assertions, while sentinel-match coverage does not explicitly require wrapper-visible `RECORDS=0` and byte-unchanged NDJSON. This leaves Bash parity and CLI idempotency behavior insufficiently specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Flesh out the batch-match bullet to mirror sentinel-match: call flush_execution_issues_main twice after seeding normalized per-section hashes in the batch, drop the sentinel between runs, assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON line count, and cleared source log. Port skills/implement/scripts/test-flush-execution-issues.sh:210-236 rather than relying on test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections alone (single call via flush_execution_issues, no rerun).
  - From Codex-Arch: Call `flush_execution_issues_main` for both sentinel-match and normalized batch-match reruns, assert `FLUSH_STATUS=already-flushed` and `RECORDS=0`, and compare each batch's pre- and post-rerun bytes.
  - From Cursor-Innovation: Spell out the rerun scenario: seed via flush_execution_issues_main, remove the sentinel, restore the same issue body, rerun main; assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON batch line count or contents, and cleared issue log.
  - From Cursor-Innovation: Add RECORDS=0 to the sentinel-match flush_execution_issues_main sub-bullets, matching the Bash harness idempotent case and Edge cases.
  - From Codex-Innovation: Specify a `flush_execution_issues_main` normalized batch-match rerun that asserts exit 0, `FLUSH_STATUS=already-flushed`, `RECORDS=0`, and unchanged batch contents.
  - From Cursor-Pragmatic: Mirror the sentinel-match bullet for batch-match: `flush_execution_issues_main`, `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged NDJSON batch contents/line count, no new record; optionally a two-call sentinel-removed rerun if you want strict parity with the current Bash per-section-probe case.
  - From Codex-Pragmatic: Specify a `flush_execution_issues_main` normalized batch-match test that asserts `already-flushed`, `RECORDS=0`, and byte-unchanged NDJSON.
  - From Cursor-Requirements: Add sub-bullets mirroring the sentinel-match block: call flush_execution_issues_main; assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON batch line count or contents, cleared issue log, and no new append. Port the per-section-probe two-call flow (seed flush, delete sentinel, rerun) or extend the existing normalized-batch test with an explicit rerun and unchanged-batch assertion.
  - From Codex-Requirements: Require a flush_execution_issues_main test that asserts already-flushed, RECORDS=0, and byte-identical NDJSON contents for the normalized-section rerun


### FINDING_2: Normal append failure must assert the complete CLI failure contract
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The normal append-failure case omits an exact stdout `RECORDS=0` assertion and, in some descriptions, an exact emitted `APPEND_LOG_FILE` assertion. A failure could therefore report an incorrect record count or log path while still passing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Parse `flush_execution_issues_main` stdout in the normal failure case and assert exact `FLUSH_STATUS=failed`, `RECORDS=0`, emitted readable `APPEND_LOG_FILE`, and exit code 1.
  - From Cursor-Requirements: Add RECORDS=0 to the normal failure-case assertions alongside exit 1 and FLUSH_STATUS=failed.
  - From Codex-Requirements: Parse CLI stdout and assert FLUSH_STATUS=failed, RECORDS=0, and APPEND_LOG_FILE equals the readable captured-stderr log, plus exit 1

