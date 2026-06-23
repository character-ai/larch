## Goal
Implement issue #5151: [IMPLEMENTING] md-to-py-IV: let failing design verbs self-log to execution-issues.md instead of prose run-log append-failure.

## Implementation Plan
## Plan

### Approach

- Keep scope to **Step 2b.5 plan-size failures** plus the reusable prose pattern.
- In `python/design_lifecycle.py`, update `step2b5_main` so it captures `plan_quality.check_plan_size_main` stdout and stderr.
- Echo only the check-size stdout back to the launcher, preserving the existing KV contract.
- When the inner check exits non-zero, write the captured stdout and stderr to `$DESIGN_TMPDIR/check-plan-size.validation.log`.
- Then call `_append_failure(...)` from inside `step2b5_main` with:
  - site: `design Step 2b.5`
  - tool: `python/cli.py plan check-size`
  - category: `Warnings`
  - exit code: the inner check-size rc
  - output file: `check-plan-size.validation.log`
- Return the original rc unchanged.
- Do not self-log wrapper setup failures that happen before `DESIGN_TMPDIR` and `CLAUDE_PLUGIN_ROOT` are available.
- Update `skills/design/SKILL.md` so the rc=2 and other-rc Step 2b.5 branches no longer instruct prompt-side `run-log append-failure`.
- Add a small pattern note: launcher-routed Python design verbs should self-log when they own the failed capture; prompt-side orchestration should only print the warning breadcrumb and continue.

## Files to modify/create

### UPDATED: `python/design_lifecycle.py`

- Replace the stdout-only capture in `step2b5_main` with stdout plus stderr capture using the existing `_capture_stdout_stderr` helper.
- Add a private `_step2b5_self_log(design_tmpdir, rc, stdout, stderr_tmp)` helper to keep the main flow readable.
- Write `check-plan-size.validation.log` only on non-zero check-size rc.
- Include both stdout and stderr in the log.
- Preserve stdout echo behavior for prompt-side KV parsing.
- Preserve the pause short-circuit before check-size runs.
- Preserve the existing `LARCH_QUIET_DISABLE=1` try/finally around the in-process `check_plan_size_main` call.

### UPDATED: `python/test_design_lifecycle.py`

- Add `test_step2b5_self_logs_on_rc2`: fake `check_plan_size_main` returns rc=2 with stdout KV, assert `check-plan-size.validation.log` written with the KV, assert `execution-issues.md` written with `plan check-size` entry.
- Add `test_step2b5_self_logs_on_rc3`: fake returns rc=3 with stderr content, assert both files written.
- Add `test_step2b5_no_log_on_success`: fake returns rc=0, assert neither `check-plan-size.validation.log` nor `execution-issues.md` created.

### UPDATED: `skills/design/SKILL.md`

- In Step 2b.5 rc=2 handling (line 518), replace the prompt-side capture-file and `run-log append-failure` command with prose noting that `python/cli.py design step2b5` already wrote the validation log and appended to `execution-issues.md`. Explicitly state the orchestrator must not write `check-plan-size.validation.log`.
- In the "Any other rc" branch (line 519), replace the append prose with the same self-logging note.
- Keep the warning breadcrumb and return behavior.

## Edge cases

- **Missing plan or missing `diff_lines`:** rc=2, stdout has `PLAN_SIZE_STATUS=` KV, stderr empty. Combined log has stdout only. Appended to `execution-issues.md`.
- **Usage or validation error (rc=3):** stdout empty, stderr has diagnostic. Combined log has stderr only.
- **Append failure:** `_append_failure` already suppresses subprocess failures. Wrapper returns original rc unchanged.
- **Pause requested:** `step2b5_main` returns pause-save rc before running check-size; no self-logging.
- **Successful check (rc=0):** Neither log file nor `execution-issues.md` entry is created. Temp stderr file deleted.

## Failure modes

1. **KV stdout no longer reaches orchestrator**: mitigation: `_print_text(out)` called before and independently of `_step2b5_self_log`.

2. **Duplicate execution issue rows**: mitigation: Remove prompt-side `run-log append-failure` prose from SKILL.md lines 518–519.

3. **Lost stderr diagnostics on rc=3**: mitigation: `_capture_stdout_stderr` writes stderr to temp file; `_step2b5_self_log` reads it into the combined log.

## Testing strategy

- Run `python3 -m pytest -q python/test_design_lifecycle.py -k step2b5`.
- Run `make py-test`.
- Run `make py-lint`.
- Run `make lint`.

## Acceptance

- At least the Step 2b.5 rc=2 / other-rc branches self-log inside Python.
- The `run-log append-failure` invocation prose is removed from those orchestrator branches.
- Establish the self-logging pattern for the other design failure branches to follow.

diff_lines: 105

## Test plan
(no test plan section in plan-file)
