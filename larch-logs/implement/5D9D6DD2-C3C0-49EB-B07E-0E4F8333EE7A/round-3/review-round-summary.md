# Review Round 3

- Mode: `diff`
- 7 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_14: read-key fd-3 contract stream is not tested under quiet mode
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pytest forces `LARCH_QUIET_DISABLE=1`, so it does not verify that `session read-key` emits values on fd 3 rather than stdout under normal quiet contract-stream behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Missing session setup reviewer presence/default pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted reviewer presence/default setup coverage was not ported, leaving degraded-tools gates, presence flags, binary-found KVs, and alias mirroring vulnerable to untested regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Missing keepalive sentinel pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted keepalive/session setup harness coverage was not ported to pytest, so regressions in `session-id` and `.larch-keepalive` side effects can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Missing local-cleanup flush-only and squash-gap pytest coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-local-cleanup.sh` cases were not ported, leaving flush-only reset, non-flush-ahead, squash-gap, branch deletion, pull, and output-KV behavior without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: entry-gate rejects an explicitly supplied empty current branch
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `entry-gate` treats `--current-branch ""` as missing, breaking detached-HEAD flows where the retired bash gate accepted an explicitly supplied empty value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: write-run-params silently accepts empty boolean flag values
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `session write-run-params` records present-but-empty router boolean flags as `false` instead of failing validation, hiding caller contract drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: cleanup-tmpdir reports success after failed removal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `cleanup-tmpdir` uses `shutil.rmtree(..., ignore_errors=True)` and exits 0 even if the tmpdir remains, preventing `implement-finalize.sh` from warning about leftover session artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


