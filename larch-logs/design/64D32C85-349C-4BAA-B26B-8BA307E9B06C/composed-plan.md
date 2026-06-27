## Plan

## Approach

- Treat `NO_SKETCHES` as binding. Draft from direct repo inspection only.
- Keep the change narrow:
  - Add an opt-in `--new-process-group` flag to `cli.py plan-review run`.
  - Use `os.setsid()` only for that flag.
  - Pass the flag only from `skills/design/scripts/design-step3-review.sh`.
  - Remove Bash monitor mode and the `monitor-mode-unavailable` prelaunch failure path.
- Keep `plan-review-loop-stderr.log`.
  - It still keeps reviewer stderr off the task stream.
- Do not change `python/cli.py`.
  - The dispatcher already forwards argv to `larch.review.plan_review.run_main`.

## Files to modify/create

### UPDATED: python/larch/review/plan_review.py

- Add a small helper near the existing Step 3 run helpers:
  - Accept an `argparse.ArgumentParser`.
  - Call `os.setsid()` when process-group isolation is requested.
  - Fail loudly with parser exit code `2` if `os.setsid` is unavailable or raises `OSError`.
  - Emit a clear `cli.py plan-review run: --new-process-group failed: ...` style message on stderr.
- Add `--new-process-group` to `run_step3_review`.
- Call the helper after parsing and after the `--read-result-env` short-circuit.
  - This keeps read-only recovery calls side-effect-free.
  - The actual review worker enters its own session before launching reviewer children.
- Leave `--record-report-evidence` unchanged.
  - `run_main` handles it before `run_step3_review`.
- Keep all existing stdout KV grammar stable.

### UPDATED: skills/design/scripts/design-step3-review.sh

- Remove monitor-mode state variables:
  - `_step3_review_monitor_was_enabled`
  - `_step3_review_monitor_enabled_by_wrapper`
  - `_step3_review_set_m_rc`
- Remove the `set -m` block.
- Remove the `monitor-mode-unavailable` hard-fail path.
- Remove every `set +m` cleanup branch.
- Keep `_step3_review_teardown_loop_group "$_loop_pid"`.
  - After Python calls `os.setsid()`, the worker pid is also its process-group id.
- Add `--new-process-group` to both `python3 ... plan-review run` launches.
- Keep `>"$_plan_review_stdout_file"`.
- Keep `2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"`.
- Remove the outer `{ ... } 2>"${DESIGN_TMPDIR}/bash-job-control.log"` wrapper.
  - There should be no Bash job-control output once monitor mode is gone.
- Replace the long #5240/#5511 comment with a short process-group comment:
  - Python owns the process-group setup.
  - Bash owns wait, status capture, process-group teardown, and fallback tmpdir cleanup.
  - The dedicated loop stderr log remains the only stderr quarantine for the worker and children.

### UPDATED: skills/design/scripts/design-step3-review.md

- Update the invariant that currently says the wrapper uses monitor mode and `bash-job-control.log`.
- State the new invariant:
  - The wrapper launches `plan-review run --new-process-group`.
  - Python calls `os.setsid()`.
  - `$!` is the process-group leader used by `kill -- -"$!"`.
  - The wrapper still redirects worker stderr to `plan-review-loop-stderr.log`.
- Remove the `bash-job-control.log` and `set -m` rationale from the contract.

### UPDATED: python/test_plan_review.py

- Add coverage for `cli.py plan-review run --new-process-group`.
- Prefer direct in-process tests for the helper or `run_step3_review` with `monkeypatch`.
- Test the opt-in path:
  - Monkeypatch `plan_review.os.setsid` to record calls.
  - Seed a cap-reached tmpdir to avoid launching real reviewers.
  - Call `run_step3_review(["--design-tmpdir", str(tmp_path), "--new-process-group"])`.
  - Assert `setsid` was called once.
  - Assert the normal cap-reached output remains valid.
- Test the default path:
  - Monkeypatch `plan_review.os.setsid` to raise if called.
  - Run the same cap-reached path without `--new-process-group`.
  - Assert it succeeds.
- Test failure handling:
  - Monkeypatch `plan_review.os.setsid` to raise `OSError("boom")`.
  - Call the CLI surface with `--new-process-group`.
  - Assert exit code `2`.
  - Assert stderr names `--new-process-group`.

### UPDATED: skills/design/scripts/test-design-step3-review.sh

- Replace the #5511 monitor-mode static guard.
- Add static assertions:
  - The wrapper must not contain `set -m`.
  - The wrapper must not contain `monitor-mode-unavailable`.
  - The wrapper must not contain `bash-job-control.log`.
  - The wrapper must pass `--new-process-group` to `plan-review run`.
  - The wrapper must still redirect worker stderr to `plan-review-loop-stderr.log`.
- Keep the runtime stderr quarantine test.
  - It should still assert the worker stderr sentinel does not reach wrapper stdout or stderr.
  - It should still assert the sentinel lands in `plan-review-loop-stderr.log`.
- Adjust comments from “job-control redirect” to “no job-control output source”.

### MAY_UPDATE: skills/design/scripts/test-step3-review-cap.sh

- Update only if the new `--new-process-group` literal affects existing grep or wrapper expectations.
- Do not add broad cap behavior changes here.
- The cap logic lives in Python and should remain unchanged.

## Edge cases

- `os.setsid()` can fail if the process is already a process-group leader.
  - Treat this as configuration failure for the opt-in flag.
  - Do not silently continue, because teardown would no longer be guaranteed.
- Child tools may create their own sessions.
  - The existing fallback `session kill-background-processes --design-tmpdir` remains after process-group teardown.
- `--read-result-env` must stay read-only.
  - Do not call `setsid` on that path.
- `--record-report-evidence` must stay independent of Step 3 worker launch.
  - Do not apply the flag there.

## Failure modes

- If `--new-process-group` fails, the worker exits before reviewer launch.
  - The wrapper captures the non-zero rc.
  - `normalize-status` handles the failed loop path.
- If a reviewer child escapes the process group, tmpdir-based cleanup is the backstop.
- If `plan-review-loop-stderr.log` is missing after wrapper launch, tests should fail.
  - This indicates stderr may leak back into the task stream.

## Testing strategy

- Run focused Python tests:
  - `python3 -m pytest python/test_plan_review.py`
- Run focused Step 3 shell tests:
  - `bash skills/design/scripts/test-design-step3-review.sh`
  - `bash skills/design/scripts/test-step3-review-cap.sh`
- Run the relevant lint target if available for changed Python:
  - `make py-lint`
- Manual smoke check, if feasible:
  - Launch the wrapper with a fake Step 3 plugin.
  - Confirm stdout contains the normal Step 3 KV envelope.
  - Confirm no `bash-job-control.log` contract remains.
  - Confirm `plan-review-loop-stderr.log` captures worker stderr.

## Acceptance

- Run focused Python tests:
  - `python3 -m pytest python/test_plan_review.py`
- Run focused Step 3 shell tests:
  - `bash skills/design/scripts/test-design-step3-review.sh`
  - `bash skills/design/scripts/test-step3-review-cap.sh`
- Run the relevant lint target if available for changed Python:
  - `make py-lint`
- Manual smoke check, if feasible:
  - Launch the wrapper with a fake Step 3 plugin.
  - Confirm stdout contains the normal Step 3 KV envelope.
  - Confirm no `bash-job-control.log` contract remains.
  - Confirm `plan-review-loop-stderr.log` captures worker stderr.

review_status: panel-failed
rounds_completed: 1
diff_added: 80
diff_deleted: 90
mechanical_churn: false
diff_lines: 170
