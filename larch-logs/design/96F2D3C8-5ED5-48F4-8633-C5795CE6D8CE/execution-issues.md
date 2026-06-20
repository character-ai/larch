### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt)

Reviewing the plan and tracing the cited code paths.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	testing	python/test_pr_body.py:30-66	Plan renames `_stamp_skipped_steps_for_terminal_report` to `_reconcile_manifest_for_terminal_report` in `python/final_report.py` but only lists `python/test_final_report.py` under Files to modify/create; `python/test_pr_body.py` still imports and calls the old private symbol in two tests	`make py-test` fails on AttributeError after the rename, or the step9a1 stamping regressions ship uncovered because the only existing unit tests for that helper are left stale	Add `### UPDATED: python/test_pr_body.py` (or fold into `python/test_final_report.py` and delete the old tests): retarget both stamp tests to `_reconcile_manifest_for_terminal_report`, keep ndjson-only `step9a1=false` coverage, and add assertions for the new `step8=true` / `status=in-progress` behavior where outcome is `pr-created`

**1. testing** (`python/test_pr_body.py:30-66`): The plan replaces `_stamp_skipped_steps_for_terminal_report` with `_reconcile_manifest_for_terminal_report` in `python/final_report.py` but only schedules test updates in `python/test_final_report.py`. Two existing tests in `python/test_pr_body.py` call the old symbol directly. Implementation will break CI unless those tests are retargeted or moved. Add `### UPDATED: python/test_pr_body.py` and migrate the ndjson-only `step9a1=false` cases plus new `step8=true` / `in-progress` assertions for `pr-created` outcomes.
## Reviewer stderr (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-3/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
✓ cursor agent: completed (exit code 0, output 1903 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and validating it against the cited code paths.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 435 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt)

Reviewing the plan and tracing the cited code paths for correctness and scope.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-5/cursor-plan-pragmatic-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
✓ cursor agent: completed (exit code 0, output 423 bytes)
  ```
