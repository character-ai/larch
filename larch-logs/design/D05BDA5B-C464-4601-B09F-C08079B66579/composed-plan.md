## Plan

## Approach

Move execution-flush behavior coverage from Bash into pytest. Keep the shell harness as a narrow delegation smoke, and make the focused target run both lanes. Do not change runtime flush logic or shard ownership.

### UPDATED: python/tests/issue/test_execution_issues.py

- Add exact `flush_execution_issues_main` coverage for missing or empty input:
  - exit `0`
  - `FLUSH_STATUS=skip`
  - `RECORDS=0`
  - Step 7a checkpoint creation
- Add a successful single-section case that verifies:
  - `FLUSH_STATUS=ok`
  - `RECORDS=1`
  - a readable `APPEND_LOG_FILE`
  - emitted NDJSON `step`, `source`, and category fields
  - sentinel creation and source-log clearing
- Add a multi-section case that verifies two NDJSON records and both categories.
- Extend preserved idempotency coverage through `flush_execution_issues_main` for the sentinel-match rerun:
  - `FLUSH_STATUS=already-flushed`
  - byte-identical execution-issues NDJSON batch contents
  - no newly recorded execution issue
- Extend normalized-section idempotency coverage through `flush_execution_issues_main` for the batch-match rerun:
  - seed the normalized per-section hashes by completing an initial flush
  - remove the sentinel and restore the same source issue body before rerunning
  - no newly recorded execution issue and cleared source log
- Add the normal flush failure case by calling `flush_execution_issues_main` with a failed run-log subprocess. Parse stdout and assert:
  - exit `1`
  - `FLUSH_STATUS=failed`
  - emitted `APPEND_LOG_FILE` equals a readable log containing captured subprocess stderr
  - append-log preservation
  - original `execution-issues.md` content plus `_append_failure` output identifying `flush-execution-issues` and `run-log exited 1`
- Preserve existing safety-net failure coverage separately from the normal append failure.

### REWRITTEN: skills/implement/scripts/test-flush-execution-issues.sh

- Replace the behavioral sandbox with an approximately 30-line delegation smoke.
- Use a controlled Python launcher to capture the selected plugin-root CLI path and complete argv.
- Verify the wrapper routes to `python/cli.py execution-issues flush`.
- Pass representative arguments, including one containing spaces, and verify byte-preserving argument forwarding.
- Make the launcher emit distinct stdout and stderr markers and a non-zero status. Verify both streams and exact exit-status forwarding.
- Remove all assertions about flush statuses, records, NDJSON content, sentinels, idempotency, and failure recording.

### UPDATED: Makefile

- Update `test-flush-execution-issues` to run the focused execution-issues pytest selection and then the rewritten Bash delegation smoke.
- Keep the target’s existing ownership and avoid adding duplicate smoke scheduling elsewhere.

## Edge cases

- Distinguish missing or empty input from a failed append.
- Assert exact record counts for successful, sentinel-match, and normalized batch-match reruns.
- Verify both idempotent reruns leave prior NDJSON batches byte-identical.
- Verify the normalized batch-match rerun after its sentinel is removed and the source log is restored.
- Keep normal flush failure coverage separate from the existing safety-net failure case.
- Preserve exact machine keys and default Step 7a source labels.
- Match Python `_append_failure` output rather than stale Bash failure substrings.

### REWRITTEN: skills/implement/scripts/test-flush-execution-issues.md

- State that pytest owns execution-flush behavior.
- Document the shell harness as a delegation-only smoke.
- List its narrow checks: plugin-root selection, CLI routing, argument forwarding, stdout and stderr passthrough, and exit-status forwarding.
- State that `make test-flush-execution-issues` runs both the focused pytest suite and delegation smoke.
- Remove claims that the shell harness validates flush behavior.

## Failure modes

- Fail the smoke if the wrapper selects the wrong plugin root, changes the command prefix, loses an argument boundary, redirects a stream, or masks the delegated exit code.
- Fail pytest if a flush branch emits the wrong status, count, record metadata, source-log disposition, idempotent batch result, append-log path, or append-failure record.

## Testing strategy

- Run `make test-flush-execution-issues`.
- Run `make lint-bash32`.
- Run ShellCheck on `skills/implement/scripts/test-flush-execution-issues.sh`.
- Confirm every removed Bash behavioral assertion has a pytest equivalent, including both idempotent rerun paths and the complete normal append-failure CLI output contract.

## Acceptance

- Run `make test-flush-execution-issues`.
- Run `make lint-bash32`.
- Run ShellCheck on `skills/implement/scripts/test-flush-execution-issues.sh`.
- Confirm every removed Bash behavioral assertion has a pytest equivalent, including both idempotent rerun paths and the complete normal append-failure CLI output contract.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 430
