### FINDING_1: Paired-PID path validation is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Paired-PID path validation is maintained separately in the writer and breadcrumb monitor, so future changes to session tmpdir scope, symlink handling, or log-root wrapping can drift between the two paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Required paired-PID writer enforcement can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Required top-level Family B paired-PID writer coverage is enforced through hand-maintained or incomplete checks, so a new required writer or removal of an existing writer call may not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Breadcrumb monitor test docs omit required test mode
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-breadcrumb-monitor.md` documents `LARCH_BM_TEST_TIMEOUT_SECONDS` without also documenting the required `LARCH_BM_TEST_MODE=1`, so contributors following that doc alone get the production timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Research collect fences conflict with foreground-only prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Research collect fences include paired-PID and monitor tokens, but surrounding prose still forbids `run_in_background`, so the monitor may not run concurrently and timeout cleanup or breadcrumb streaming may not work as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: KILL escalation test relies on brittle wall-clock timing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Test 20 requires elapsed time to be at least 5 seconds to prove KILL escalation, but platforms where `trap "" TERM` does not ignore SIGTERM can exit earlier and flake CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Nested Family B parent env unset is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Removing `unset LARCH_PAIRED_PID_FILE` before nested Family B calls such as `ci-wait` would not fail CI, allowing a nested writer to clobber the parent PID file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Ship PR writes paired PID too late
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` writes the paired PID only after long validation, so if startup blocks before the write, the monitor can time out with an empty PID file and leave background work running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Large Family B integration harnesses do not cover paired PID
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Real `ship-pr` or `collect-agent-results` paired-PID regressions may only surface in a full implement run because the large integration harnesses were not extended to exercise writer plus monitor behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Paired-PID read can race symlink replacement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The breadcrumb monitor validates then reads the paired PID file without a non-following open, so a same-UID process able to replace the file can race in a symlink target and cause signaling of an unintended PID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Leading-zero PID input is accepted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: All-digit paired-PID parsing accepts leading zeros, which can make tampered values ambiguous before `kill`; the monitor should reject or normalize such input and reject non-positive PIDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Timeout path ignores done sentinel after signaling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After timeout signaling, the monitor always exits 4 without re-checking the done sentinel, so a successfully exiting Family B process can still be reported as a monitor timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Research collect lacks exported tmpdir for paired-PID writer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `collect-agent-results` depends on an exported session tmpdir for paired-PID writing, but research fences omit `export RESEARCH_TMPDIR`, so the writer can fail open and leave the monitor unable to signal an orphaned background process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Single-PID signaling may miss nested long-running children
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Monitor timeout signaling targets only one PID, which may kill a top-level Family B parent while nested long-running child processes continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Paired-PID writer failures are not visible enough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When paired-PID writing fails because of an invalid path or missing exported tmpdir, the writer can leave an empty file with only a quiet-log warning, and the monitor later cannot signal the background process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Malformed paired-PID read failures share one warning
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Different paired-PID read failure modes all surface as `paired-pid-file-missing`, making timeout debugging harder for operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Breadcrumb publish duplication is already consolidated
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Breadcrumb publish duplication was already consolidated through `larch_log_publish_breadcrumbs_shared`; the source reviewer marked this as pre-existing/no action for the current scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Collect paired-PID write is deferred past argv parsing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `collect-agent-results` writes the paired PID after argv parsing rather than immediately after trap setup, so bad argv or very fast timeout tests can leave the paired-PID file unset while the monitor waits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Test timeout mode requirement has plan traceability gap
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The implemented timeout hook requires `LARCH_BM_TEST_MODE=1`, while the original plan text specified only `LARCH_BM_TEST_TIMEOUT_SECONDS`; the reviewer framed this as a traceability concern rather than a functional bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
