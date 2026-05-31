Verifying a few high-impact findings against the code so merged concerns stay accurate.
Structured aggregator output (plain text for `aggregator-output.txt`):

### FINDING_1: run_lint_fix monolithic function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` combines validation, dispatch, git guards, forbidden-path reversion, and auto-commit in one ~315-line function. Parity fixes to `lint-fix-loop.sh` require editing a single giant function and brittle multi-call stub sequences in `test_checks.py`. Extract phase-aligned private helpers (`_prepare_baseline`, `_dispatch_agent`, `_finalize_delta`) while keeping the public API unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: checks.py god-module size and layout
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: ~1.6k-line module with 38 functions spans capture, dispatch, git loop, and escalation. Phase 5+ CI fixer work will add more surface to an already hard-to-navigate module; flat layout prevents directory split. Add internal section boundaries and document seams; consider `checks_dispatch.py` sibling if flat constraint relaxes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_12: duplicate incompatible StubRunner implementations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Duplicate incompatible `StubRunner` implementations in `test_checks.py` and `test_git.py` with different matching semantics. `proc.Runner` signature changes (fd redirect) must be updated in multiple places, risking test drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: _run_cursor direct Path filesystem checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_run_cursor` uses direct `Path` filesystem checks alongside injected `Runner`. Stub tests cannot fully cover stderr-tail selection branches without real files on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_14: lint-fix-loop mkdtemp run dirs never cleaned up
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `mkdtemp` run directories under lint-fix-loop are never cleaned up. Long implement runs with repeated fix attempts accumulate orphaned run dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_15: redaction write failure overwrites exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Redaction write failure forces `exit_code=1` instead of preserving `relevant-checks.sh` return code. Callers use exit code 126 vs 1 to distinguish non-executable script from redaction I/O failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_16: repo_root used without git toplevel verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `repo_root` is used as cwd and agent workspace without git toplevel verification unlike `lint-fix-loop.sh`. Phase 7 wiring with a tampered session `REPO` path could run relevant-checks and codex/cursor `--full-auto` against an unintended directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: TOCTOU on dispatch_first redacted log path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `dispatch_first` uses `is_file()` on redacted log path without immediate `_resolve_checks_log_path` re-check. TOCTOU symlink swap in a shared session directory could steer the fixer at sensitive file contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: bare except around relevant-checks run loses log context
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bare `except Exception` around `relevant-checks.sh` run loses `raw_log_path`. Runner faults masquerade as check failures without log path for loop accounting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: structural fix failures mapped to dispatch-failed TRANSIENT
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Structural fix failures map to `dispatch-failed` `TRANSIENT` like bash. Forbidden-path or missing launcher failures may hit transient recovery instead of stall when wiring ship-pr.
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

### FINDING_23: _read_log_tail trivial wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_read_log_tail` is a trivial wrapper around `_read_log_text_bounded` with extra indirection and no behavioral value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_24: _submodule_paths redundant collection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_submodule_paths` triple-collects submodule paths with redundant `.gitmodules` regex parse—extra I/O and dedup logic on every fix dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_25: LoopResult mutable vs frozen dataclasses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LoopResult` is mutable while other result dataclasses are frozen—inconsistent immutability convention from Phase 4 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_26: per-job target command string API vs args file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Per-job target command is a string API; bash reads `--target-cmd-args-file`. Phase 7 integrator must parse args file externally or per-job prompt text diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_27: main-agent-required test omits failure_reason=dispatch-failed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `main-agent-required` loop test omits `failure_reason=dispatch-failed`. Subtle change to `FixOutcome` metadata for #3207 would not be asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_28: run_lint_fix allowed_root fallback when allowed_tmpdir is None
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `run_lint_fix` `allowed_root` falls back to parent of `run_parent` when `allowed_tmpdir` is None. Direct API misuse could feed a checks_log outside `IMPLEMENT_TMPDIR` while `run_parent` stays under session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_29: unchecked stat in _compose_prompt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Unchecked `checks_log.stat` in `_compose_prompt`. Log removed between resolve and compose can raise uncaught `OSError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] test_checks.py single large module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test file rivals implementation size in a single module—harder to navigate over time, introduced by this feature not a pre-existing regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] lint-literal-counts larch-logs exclusion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `larch-logs` markdown exclusion is ancillary branch hygiene, not Phase 4 checks scope; already flagged in `python/README.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] test-ship-pr.sh does not exercise Python checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Bash RCC loop harness does not exercise Python checks module—pre-existing; Python/bash divergence possible until Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] README classify_launch_failure doc tension
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: README documents no `classify_launch_failure` on local path—pre-existing doc/plan wording tension only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] bash compose_prompt unredacted log metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash `compose_prompt` exposes unredacted log path metadata and raw log tail in fixer prompt—pre-existing live path; mitigated when ship-pr passes `.redacted.log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] target_cmd_display backtick injection in fixer prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `target_cmd_display` backtick injection in fixer prompt—malicious CI job display string could distort fixer instructions; same pattern in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] proc.run FD mode CommandResult capture contract
- **Reviewer(s)**: dyn-subprocess-fd-contract-output.txt
- **Severity**: nit
- **Concern**: When callers pass a raw FD, `CommandResult.stdout` / `stderr` are always `''`; safe for current `checks.py` readers but breaks nominal `str` capture contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-fd-contract-output.txt: Document FD mode in the `Runner` protocol or return a sentinel / optional bytes field.

### OOS_8: [OUT_OF_SCOPE] FD redirect test gap noted only in dyn review
- **Reviewer(s)**: dyn-subprocess-fd-contract-output.txt
- **Severity**: latent
- **Concern**: Pre-existing framing: no `test_proc.py` coverage of FD redirect branch; parity test in `test_checks_bash_parity.py` is the right catch once `proc.run` is fixed—subsumed for in-scope action by FINDING_9.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-subprocess-fd-contract-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] cursor wrapped prompt rstrip newline divergence
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: nit
- **Concern**: After the `X` sentinel, `wrapped.rstrip("\n")` can strip trailing newlines that bash keeps via `${_wrapped_prompt%X}` only—low risk per script contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] Python omits _lint_fix_set_stderr_tail_stem on agent failure
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: nit
- **Concern**: Bash calls `_lint_fix_set_stderr_tail_stem` on codex/cursor failure; Python only calls `_write_failed_agent_stderr_tail`—may affect downstream stderr-tail stem wiring, not argv shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] codex artifact pre-delete timing vs bash lock order
- **Reviewer(s)**: dyn-dispatch-argv-parity-output.txt
- **Severity**: latent
- **Concern**: Pre-delete of codex artifacts runs before `_run_with_serial_lock`; bash deletes after lock acquire—unlikely unless another process races on the same `run_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dispatch-argv-parity-output.txt: Address the concern above.

---

**Subsumed (not emitted as findings):** Input **FINDING_40** (FD close ordering vs `runner.run` blocking)—reviewer concluded no change required; optional comment only, not a behavioral risk. Input **FINDING_42** in-scope test gap is covered by **FINDING_9**.
