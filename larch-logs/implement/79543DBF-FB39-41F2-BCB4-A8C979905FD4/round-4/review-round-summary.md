# Review Round 4

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_10: dirty-tree bad sidecar path validation lacks test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Invalid `--sidecar` path handling has no direct test. Regressions could stop emitting `REASON=bad-sidecar-path` or write under bad metadata names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: bootstrap invoke exit-2 empty-stdout contract lacks assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Bootstrap failure tests do not assert empty stdout on rc 2. Orchestrator stdout parsing could consume `STEP_FAILED` routing lines on bootstrap failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: emergency-bypass append fallback was dropped
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Emergency-bypass logging no longer falls back from `append-failure` to `append-entry`. If `run-log append-failure` fails once, Step 0 aborts with `STEP_FAILED=emergency-bypass-log` instead of continuing as the old harness covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: resume plan-tail reruns tracking side effects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `bootstrap invoke --mode resume` always runs tracking side effects on the branch-1-resume path. Dirty-tree resume can rerun rename, run-log init, or tracking post work and stall with `tracking-init-failed`. Resume plan-tail with a matching sentinel should return before tracking side effects, matching the Bash early return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: bootstrap quiet routing can bypass stdout capture
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `bootstrap invoke` does not disable inherited quiet routing. With `LARCH_QUIET_ACTIVE=1` and fd 3 inherited, contract KVs can bypass `redirect_stdout`, leaving captured output empty and turning a successful bootstrap into exit 1. Set `LARCH_QUIET_DISABLE=1` before emitting KVs in invoke and bootstrap entrypoints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: preflight fetch lost transient retry
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python preflight runs `git fetch` without the retired Bash transient retry wrapper. A one-time DNS, TLS, connection reset, HTTP 502, or HTTP 5xx failure can abort `/implement` with exit 3 instead of retrying. Recreate the old transient retry policy and add regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: implement env pointer refresh failures are silent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-implement-env` pointer refresh failures are ignored. SessionStart or progress reporting can identify the wrong active implement tmpdir without an execution-issues warning. Capture stderr and append a redacted run-log failure warning on nonzero exit while continuing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: dirty-tree scope-check and scope-marker CLI contracts lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required dirty-tree CLI boundary contracts are untested. Regressions in `scope-check` rc 0/1/2 or `scope-marker` rc 0/1/2 could break malformed-manifest recovery and plan-review gates while passing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: bootstrap-routing.env non-regular write refusal lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Symlink and non-regular destination refusal for `bootstrap-routing.env` is untested. A regression could overwrite or follow a symlink despite the atomic-write safety contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


