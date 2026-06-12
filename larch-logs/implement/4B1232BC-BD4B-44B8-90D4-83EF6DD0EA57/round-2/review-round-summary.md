# Review Round 2

- Mode: `diff`
- 16 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Health-gate timeout ignores session-env resolution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_health_gate_timeout` does not honor the bash three-tier timeout resolver. Session-env opt-outs such as `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` may be ignored, causing Python to run or fail the health gate when bash would disable it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Cursor CI skips Darwin keychain preread
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `launch_cursor_ci_main` does not port the Darwin keychain preread behavior from bash. On Darwin, CI-fix launches may fail under concurrency when `CURSOR_API_KEY` is empty but a keychain token exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Claude CI passes prompt content on argv
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude CI prompt content is passed on argv. Prompt text may be visible in process listings while Claude runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Retired launcher harness coverage is not pytest-equivalent
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted launcher harnesses were replaced by thin pytest coverage. Plan-required contracts for launchers, health gate, serial locks, Codex exec ordering, run-external-agent validation, trusted instructions, outer metadata, and Cursor CI may regress while Makefile targets remain green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Makefile launcher aliases lost timeout-zero contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple Makefile harness targets now alias to `pytest test_agents.py -q`, and the dedicated `--timeout 0` contract has no equivalent pytest. Removing the exact validation error may no longer fail `make test-run-external-agent-args`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Context rendering redaction and XML escaping tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_render_context_files` implements secret redaction and XML escaping, but pytest does not assert those invariants. Secret or markup bytes could leak into a Claude prompt or break prompt structure without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Degraded-tools gate pytest coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The degraded-tools gate has only one pytest case compared with the deleted harness matrix. Env-var fallback, warning behavior, flag precedence, and both-down cases may regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Cursor CI stall monitor was not ported
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_cursor_ci_main` does not preserve Cursor CI stall monitoring. A stalled child can wait until the full timeout instead of `LARCH_CURSOR_CI_STALL_THRESHOLD`, and required stall JSON, diagnostics, role-specific channels, and child-first termination may be missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_20: SECURITY.md still documents deleted launcher scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still references deleted launcher scripts as live invocation surfaces. Operators may configure or audit removed paths instead of the Python agent CLI verbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_24: Collector cannot retry legacy Codex exec metadata
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results.sh` rejects legacy `OUTER_LAUNCHER` metadata for deleted `launch-codex-exec.sh`. Pre-cutover or fixture `.meta` files may fail empty-output recovery instead of replaying through the Python CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_25: Dispatch voter harness stubs impossible agent executable paths
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retained dispatch voter harnesses stub impossible space-containing agent executable paths instead of intercepting `python/cli.py agent` argv. Tests may fail unexpectedly or invoke the real Claude launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: CI launchers omit failure class and reason KVs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python CI launchers no longer emit `LAUNCHER_FAILURE_CLASS` and `LAUNCHER_FAILURE_REASON`. `ship-pr.sh` may default missing classes to health and continue the waterfall when non-health failures should short-circuit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Claude subprocess sidecar, dirty-tree, and accounting contracts regressed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_subprocess` does not preserve dirty-tree, failure carrier, cleanup, and token accounting contracts. Success may record `STATUS=unknown`, malformed or nonzero Claude runs may lack stderr-tail or failure diagnostics, and `/report-tokens` may undercount Claude subprocess usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Health-gate pytest matrix is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Plan-required health-gate matrix tests were not ported to pytest. Regressions in timeout opt-out resolution, unhealthy return codes, and fail-open probe parsing may ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Darwin serial lock is not held for auth retries
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Darwin serial lock wraps only the first spawn attempt. After an auth-class failure, retry attempts may spawn Codex or Cursor without the per-tool startup mutex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Claude subprocess prompt-file containment was dropped
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude subprocess prompt-file validation no longer enforces safe roots or rejects unsafe paths. A caller may pass an arbitrary readable local file and send its contents to Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


