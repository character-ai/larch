# Review Round 1

- Mode: `diff`
- 16 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Branch-1 resume skips required tracking side effects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Branch-1 resume can return before rename, run-log init, run-flag persistence, and metadata posting. Crash-resume after the sentinel write can leave downstream run-log state uninitialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Empty RUN_ID is accepted during tracking adoption
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `resolve_run_id` can return an empty string. Branch-2 adoption can proceed without a valid `LARCH_RUN_ID` and pass a bad run id to run-log init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Session env rewrite can drop preserved keys
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_write_base_session_env` can overwrite `session-env` without merging prior keys. Post-tracking rewrites can drop keys expected by downstream helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Resume plan-tail skips emergency bypass append
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-contract-fidelity-output.txt
- **Severity**: important
- **Concern**: Resume plan materialization can skip emergency bypass log consumption and audit entries. This diverges from the old dual call-site behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-contract-fidelity-output.txt: Call `_append_emergency_bypass(st)` on the resume branch too (before `_persist_run_flags`), matching the old dual call-site behavior and the plan’s no-replay-on-resume contract via the consumed sentinel.


### FINDING_17: Fresh bootstrap omits claude-source token artifacts
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fresh bootstrap no longer creates `claude-source.env` or persists `LARCH_CLAUDE_SOURCE_FILE`. External implementer token accounting can lose transcript source context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Session setup preflight cutover is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `session_env.py` admission preflight behavior is not tested because session setup tests all use `--skip-preflight`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Review-core default Python dirty-tree path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `review-core.sh` tests only stub override paths. The default `python3 cli.py dirty-tree checkpoint/baseline` invocation can regress without harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Tracking adoption helper failures are ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Tracking rename, run-log init, run-flag persistence, and post-tracking metadata failures can be ignored. Step 0 can continue with missing logs, missing deferred state, or absent tracking-init-failed stall routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-architecture-output.txt: Capture the `_cli("run-log", "init", …)` result, persist stderr to the session tmpdir on failure, set `st.implement_bail_reason = "tracking-init-failed"` and `st.stall_tracking = "true"`, skip sentinel/post-tracking work, and port the old harness cases for this bail branch into `python/test_bootstrap.py`.


### FINDING_21: Quiet routing can steal machine-readable CLI output
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python contract CLIs can inherit quiet routing and emit `KEY=value` output to FD3 instead of captured stdout. Bootstrap invoke, admission command substitution, and dirty-tree callers can receive empty output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Set `LARCH_QUIET_DISABLE=1` at the start of these machine-output CLI entrypoints, especially `bootstrap invoke`, `admission preflight`, `admission fork-env`, and dirty-tree `baseline` / `checkpoint`, and add regression tests with inherited `LARCH_QUIET_ACTIVE` / `LARCH_QUIET_PID`.


### FINDING_22: Bootstrap phase exceptions can become tracebacks
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `run_bootstrap()` catches only `BootstrapExit`. Other exceptions in phase code can escape as tracebacks instead of bounded `STEP_FAILED=` output with exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Wrap the phase pipeline in a top-level `try/except Exception` in `run_bootstrap()` (and optionally `invoke_main()`), map unexpected failures to `emit_step_failed("…")` or a synthetic `STEP_FAILED=internal-error`, and add pytest cases that inject I/O failures to assert exit **2** plus empty invoke stdout.


### FINDING_3: Emergency bypass logs are appended without legacy validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-contract-fidelity-output.txt
- **Severity**: important
- **Concern**: Emergency bypass handling can append malformed, stale, or wrong-issue bypass logs as valid audit data. The Python path omits BYPASS grammar checks, canonical kind checks, wrong-issue rejection, invalid-format redaction, fallback append behavior, consumed-sentinel semantics, and double-failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Port the legacy validation and fallback append path, including expected-issue checks, redacted invalid-format entries, consumed-sentinel behavior, and the `STEP_FAILED=emergency-bypass-log` double-failure case.
  - From dyn-architecture-output.txt: Port `append_emergency_bypass_log_if_present()` logic into a dedicated helper in `python/bootstrap.py` (or a small submodule), keep the consumed sentinel, and restore the plan’s pytest matrix for valid/invalid/wrong-issue/no-replay/double-failure cases.
  - From dyn-contract-fidelity-output.txt: Port the full `append_emergency_bypass_log_if_present` logic from `scripts/implement-bootstrap.sh` (validation, redaction, invalid-format fallback with exit 99 semantics, double-failure handling) into `_append_emergency_bypass`.


### FINDING_34: Coder fallback drops warning and manifest side effects
- **Reviewer(s)**: dyn-contract-fidelity-output.txt
- **Severity**: latent
- **Concern**: `_phase_coder` preserves routing values but can drop operator-facing warnings and execution-log or manifest fallback side effects required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-fidelity-output.txt: Reintroduce the Bash warning/manifest helpers (or equivalent Python calls to `run-log append-failure` and the manifest writer) on every fallback branch in `_phase_coder`.


### FINDING_4: Plan materialization omits tally and tracking summary
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_phase_plan` can complete without writing the plan-review tally or posting/upserting the `larch:plan` tracking issue summary. Downstream run-log and issue workflows then miss expected artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Deleted Bash harness coverage lacks pytest parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-contract-fidelity-output.txt
- **Severity**: important
- **Concern**: Replacement pytest coverage is much thinner than the deleted Bash harness surface. Bootstrap, admission, fork-env, dirty-tree, emergency-bypass, routing, and contract exit paths can regress while Makefile targets stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Port the required harness cases before deleting the Bash harnesses, or keep the old harnesses until equivalent pytest coverage exists.
  - From dyn-architecture-output.txt: Either restore parity coverage in the three pytest modules (starting with `STEP_FAILED` arms, routing-envelope allowlist equality, admission resume/`gh` ordering, and dirty-tree baseline/meta-path cases) or keep the Bash harnesses until pytest reaches equivalent breadth; do not treat Makefile retargeting alone as contract preservation.
  - From dyn-contract-fidelity-output.txt: Add the planned `test_gate_*`, `test_preflight_*`, and `test_fork_env_*` cases from the issue plan so Makefile retargets are backed by real parity tests.
  - From dyn-contract-fidelity-output.txt: Implement the planned `test_invoke_*`, `test_emergency_bypass_*`, `test_coder_select_*`, and routing-file write tests so retired `test-implement-bootstrap*.sh` coverage is not lost.


### FINDING_8: Forked issue view can target the wrong repo when upstream is missing
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-fidelity-output.txt
- **Severity**: important
- **Concern**: Forked bootstrap can call `gh issue view` without `--repo` when `upstream_repo` is empty. It can fetch the fork copy instead of failing closed against the upstream design issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-contract-fidelity-output.txt: Mirror the Bash guard: if `forked_target == "true"` and `upstream_repo` is empty, write the same stderr diagnostic and emit `STEP_FAILED=gh-issue-view` before invoking `gh`.


### FINDING_9: Subprocess launch errors can escape structured failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Missing commands such as `gh` can raise `OSError` or `FileNotFoundError` instead of producing documented structured outputs like `ADMISSION_ERROR` or `STEP_FAILED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


