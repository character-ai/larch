# Review Round 2

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_monitor` uses `child_identity` out of scope
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `_monitor` can hit `NameError` on timeout or orphan paths because it reads `child_identity` outside scope, which prevents `BGJOB_RC=timeout` / `BGJOB_RC=orphaned` from being written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Pass child identity into _monitor and test timeout/orphan without mocking _monitor
  - From codex-specialist-edge-cases: Pass recorded child identity into _monitor and test timeout and orphan result env writes
  - From codex-specialist-testing: Pass the recorded child identity into _monitor and use that variable on timeout/orphan branches.


### FINDING_2: launcher PID is treated as the owner identity
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Defaulting owner identity to the short-lived launcher can make long jobs look orphaned after the launcher exits even while Claude is still alive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Wire session owner PID into every bgjob start and fail closed when capture fails
  - From codex-specialist-edge-cases: Require or derive the real session owner pid and fail closed when it cannot be captured


### FINDING_3: `wait` can report `DEAD` before the result exists
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: When the child has exited but the daemon is still alive, `wait` can misclassify a successful job as `DEAD` before the result env is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Keep waiting while daemon is live; emit DEAD only when daemon is gone without result
  - From codex-specialist-edge-cases: Treat dead child plus live daemon as pending and report DEAD only when daemon is gone with no result
  - From codex-specialist-testing: Only return DEAD when the daemon is gone and the result env is still absent; keep polling until the result appears.


### FINDING_4: registry paths are trusted without containment checks
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Stored registry log/result paths can be used to escape the expected job root, letting `wait` or `reap` read arbitrary files or tails outside the session tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Recompute paths under tmpdir/step or reject escaping/symlinked paths on read
  - From codex-specialist-edge-cases: Recompute or validate stored paths under $TMPDIR/bgjob and reject symlinks or non-regular files
  - From codex-specialist-testing: Reject any stored path that does not resolve beneath the expected tmpdir or log root and reject symlinked or escaped paths.


### FINDING_5: post-`Popen` startup failure can leak the child process
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: If identity capture fails after `Popen`, the spawned child can survive without registry or result cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Kill the child process group on any post-Popen startup failure
  - From codex-specialist-edge-cases: Terminate the just-spawned child or process group on every post-Popen failure before returning


### FINDING_6: daemon log opens can follow a symlink race
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A symlink swapped in after validation can redirect daemon output outside the session root when the log file is opened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Open logs with O_NOFOLLOW plus append/create flags and verify regular files under the log root


### FINDING_7: no-`jq` deny path can fail to emit deny JSON
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: When `jq` is unavailable, the hook can exit without emitting valid deny JSON for `run_in_background:true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Use shell printf for constant deny JSON in the no-jq branch or hard-require jq before denial paths


