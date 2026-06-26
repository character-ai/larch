### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/checks.py:301-312
- **Concern**: The planned private timing helper does not take or use the existing Runner, but test_checks.py assertions require StubRunner.calls.. Scenario: The helper spec only says to invoke python/cli.py timing record-vendor-task with env vars. test_checks.py plans to assert a timing record-vendor-task runner call. _mark_step_ledger already records timing through runner.run. A subprocess-only helper would pass runtime but fail the mandated tests and diverge from the established checks.py pattern.
- **Proposed resolution**: Add runner: Runner to the helper signature and invoke record-vendor-task through runner.run with the same IMPLEMENT_TMPDIR / LARCH_TIMING_SKILL / DESIGN_TMPDIR env contract as _mark_step_ledger.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py:89-106
- **Concern**: The run_lint_fix refactor bullets still omit explicit outcome = None and start_s capture even though Failure modes require them.. Scenario: run_relevant_checks bullets (lines 75-76) require both.initializations. run_lint_fix bullets jump straight to try/finally without them. An implementer following only the lint-fix subsection can hit UnboundLocalError in finally on exceptions or emit rows with a missing/wrong start_s, recreating the silent-gap bug class on lint-fix exception paths.
- **Proposed resolution**: Add the same two bullets to the run_lint_fix wrapper spec as run_relevant_checks: initialize outcome = None and capture start_s = int(time.time()) before the try block.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_timing.py:186-187
- **Concern**: The test_timing.py update is an incomplete sentence and does not name the new task kinds.. Scenario: The plan says to extend accepted-kind tests and assert no unknown task-kind warning, but the parameterized kinds line is blank. Without claude-relevant-checks and claude-lint-fix in test_timing.py, allow-list drift can ship and every new wrapper call will emit stderr warning noise despite timing.py being updated.
- **Proposed resolution**: Complete the bullet: parametrize claude-relevant-checks and claude-lint-fix in a test_timing_record_vendor_task_accepts_* test mirroring the existing review-fix parametrized pattern, and assert unknown task-kind is absent.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py:89-106
- **Concern**: Prior accepted fix incomplete: `run_lint_fix` wrapper bullets still omit explicit `outcome = None`, `start_s = int(time.time())`, and `return outcome` even though `run_relevant_checks` lists them and Failure modes require the full envelope. Scenario: Round 2 accepted the missing try/finally envelope; the current plan only says "mirror exactly" for lint-fix. A literal implementer can wrap `_run_lint_fix_impl` without initializing `outcome`, without capturing `start_s`, or with `return` inside `try`, leaving exception paths unlabeled or successful paths without `--start-s`/`--end-s`
- **Proposed resolution**: Copy the explicit `run_relevant_checks` bullets into the `run_lint_fix` section: initialize `outcome = None`, capture `start_s` before `try`, assign `outcome = _run_lint_fix_impl(...)` inside `try` only, compute `end_s = int(time.time())` in `finally`, then `return outcome` after the block



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/checks.py:49-68
- **Concern**: New private timing-record helper spec does not route through the `Runner` passed into `run_relevant_checks` / `run_lint_fix`, unlike `_mark_step_ledger`. Scenario: The test plan requires `StubRunner` assertions on `timing record-vendor-task` calls. A helper that shells out directly (as `_record_coder_vendor_task` does in `review_and_fix.py`) will not populate `runner.calls`, so the planned source-level tests cannot observe recording without extra monkeypatching
- **Proposed resolution**: Define the helper as `_record_checks_vendor_task(*, runner: Runner, ...)` and invoke `runner.run([...])` with the same env pattern as `_mark_step_ledger`; call it from both public wrappers with the existing `runner` argument



