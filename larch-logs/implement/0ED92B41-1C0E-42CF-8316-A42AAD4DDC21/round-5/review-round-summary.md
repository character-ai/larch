# Review Round 5

- Mode: `diff`
- 14 accepted, 15 rejected (14 exonerated)

## Accepted Findings

### FINDING_10: _run_codex bash -c exec mis-expands $@
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: important
- **Concern**: `_run_codex` wraps `run-external-agent.sh` in `bash -c 'exec "$@" >"$1" 2>"$2"'` with `$1`/`$2` set to `codex.events.jsonl` and `codex.wrapper.log`. Under bash `-c`, `"$@"` expands from `$1` onward, so `exec` tries to run the events path as the executable instead of `run-external-agent.sh`, diverging from `lint-fix-loop.sh:245-252`. Stub unit tests never execute this shell, so argv-parity assertions can pass while real dispatch fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Use offset slicing, e.g. `exec "${@:3}" >"$1" 2>"$2"`, or drop the inner wrapper and pass stdout/stderr redirection through `Runner` the way bash does; add a small integration test that runs the wrapper against a no-op leaf and asserts the intended process is exec'd.


### FINDING_11: _run_cursor bash -c exec mis-expands $@
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: important
- **Concern**: `_run_cursor` uses `bash -c 'exec "$@" >"$1" 2>&1'` with only `cursor.wrapper.log` before `*argv`, so `"$@"` is `wrapper.log` plus the real argv and `exec` targets the log file instead of `run-external-agent.sh`, unlike `lint-fix-loop.sh:290-296`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Same pattern as codex, e.g. `exec "${@:2}" >"$1" 2>&1`, or equivalent non-shell redirection; cover with an integration test.


### FINDING_18: bare except around relevant-checks run loses log context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bare `except Exception` around `relevant-checks.sh` run loses `raw_log_path`. Runner faults masquerade as check failures without log path for loop accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: no run_checks_phase dispatch_first integration test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No `run_checks_phase(..., dispatch_first=True)` integration test. Top-level wiring bug for dispatch-first CI shape could ship while `run_check_fix_loop` unit tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: plan/acceptance drift on agents.classify_launch_failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan lists `errors.py` import / `agents.classify_launch_failure` for dispatch failures; implementation uses `main-agent-required` + `dispatch-failed` per `lint-fix-loop.sh` #3207 and never imports `agents`. Future maintainers may wire CI classifiers into local fixer per stale acceptance text and break #3207 parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align plan with actual imports.
  - From cursor-specialist-plan-fidelity-output.txt: Update plan/acceptance/README to document that local fixer dispatch does not use agents classifiers; keep tests asserting `classify_launch_failure` is not called.


### FINDING_22: cursor preflight stderr not appended to preflight_log
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: latent
- **Concern**: Cursor preflight in bash runs `cursor-wrap-prompt.sh` with stderr appended to `cursor.preflight.log` (`lint-fix-loop.sh:285`). Python runs the same script via `runner.run` with no `2>>` redirect, so wrap-time errors go to default stderr capture and are not in `preflight_log`. On failure, `_write_failed_agent_stderr_tail` prefers an empty preflight file, weakening parity with `_run_cursor_record_early_fail` in `lint-fix-loop.sh:261-287`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Mirror bash with a subshell redirect, e.g. `bash -c '"$1" "$2"; s=$?; printf X; exit $s' bash … 2>>"$preflight_log"`, or merge captured stderr into `preflight_log` before tail extraction.


### FINDING_27: main-agent-required test omits failure_reason=dispatch-failed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `main-agent-required` loop test omits `failure_reason=dispatch-failed`. Subtle change to `FixOutcome` metadata for #3207 would not be asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: bash-parity harness untracked and incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_checks_bash_parity.py` exists locally but is untracked and excluded from branch diff/CI. Harness is incomplete vs acceptance (no lint-fix-loop fix-attempt accounting; missing no-changes-stale cap and main-agent-required cases). Branch ships semantic-only stub tests; loop and capture argv parity vs bash are unverified—`make py-test` can stay green while `normalize_max_iter`, captured-check parsing, and related bash semantics drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: ship-pr RCC loop parity not exercised in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Committed/local bash parity does not compare `run_check_fix_loop` / `run_checks_phase` to `ship-pr.sh` `run_captured_cmd_then_fix_loop`. Python loop status strings can diverge from bash `_RCC_STATUS` on dispatch-first or empty-failure paths without CI failure. `test_parity_run_check_fix_loop_empty_failure_exhausted` is Python-only unless relabeled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ship-pr-sourced loop parity harness modeled on `scripts/test-ship-pr.sh` RCC stubs.
  - From cursor-specialist-plan-fidelity-output.txt: Add bash-sourced parity for empty-log exhausted or relabel test as Python-only regression.


### FINDING_5: run_checks_phase missing check-first no-changes short-circuit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `run_checks_phase` uses a generic check-first RCC loop, but live `ship-pr` Step 6 stops after no-changes when checks still fail. In Python, when checks fail, fixer returns no-changes, and checks still fail, the loop can re-dispatch the fixer until `max_iter` (default 3) and end exhausted instead of matching Step 6 stall semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: on-demand redaction after capture redaction failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On-demand `_redacted_log_for_dispatch` runs when capture left `redacted_log_path` None but `raw_log_path` set. Bash capture exits `redaction-failed` and never dispatches a fixer; Python loop can still on-demand redact and call `run_lint_fix`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: fallback redacted log filename diverges from capture
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fallback redacted path is `*.log.redacted` vs capture `*.redacted.log`. Operators and path guards see different filenames after redaction fallback; parity with `run-relevant-checks-captured.sh` breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: validate_tmpdir empty XDG_CACHE_HOME bypass
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `validate_tmpdir` honors empty `XDG_CACHE_HOME` as `Path("")`, so cache sessions resolve under process CWD instead of `$HOME/.cache`. A hostile or mis-set environment (`XDG_CACHE_HOME=""`) plus writable CWD can make `claude-implement-*` dirs under `./larch/sessions` pass validation and store/read checks logs outside the intended cache root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_9: proc.run FD redirect passes errors= with text=False (Python 3.12)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-subprocess-fd-contract-output.txt
- **Severity**: important
- **Concern**: `run_relevant_checks` passes a real log FD as both `stdout` and `stderr` (`checks.py:355-359`), so `proc.run` takes the non-`PIPE` branch with `popen_text=False` but still passes `errors="replace"` into `subprocess.Popen` / `subprocess.run`. In Python 3.12 binary mode that raises `ValueError: errors must be None`. The only production caller of raw FD redirect is this path; unit tests use `StubRunner`, which never calls `proc.run`, so the defect is masked in `test_checks.py`. `test_checks_bash_parity.py` (`_ProcRunner` → real `proc.run`) should fail on `py.phase == "agent-lint"` because `checks.py:361-370` catches the exception and returns a generic `exit_code=1` / `phase="unknown"` with no log content. Related gap: `proc.run` fd-redirect paths lack unit tests in `test_proc.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-fd-contract-output.txt: Only pass `errors="replace"` when `popen_text` is true (or set `encoding="utf-8", errors="replace"` for the PIPE path only). Add a `test_proc.py` case that runs a trivial command with `stdout=<open fd>` and asserts no exception and that bytes land in the file.
  - From cursor-specialist-structure-output.txt: Add `test_run_redirects_to_fd` in `test_proc.py`.
  - From cursor-specialist-testing-output.txt: Extend `test_proc.py` with fd stdout/stderr subprocess cases.


