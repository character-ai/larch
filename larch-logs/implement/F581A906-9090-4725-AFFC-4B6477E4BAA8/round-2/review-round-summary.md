# Review Round 2

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Cached fixer run IDs are not bound to current identity
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: The wrapper may reuse a cached `RUN_ID` from `fixer-status.env` without verifying that `STARTING_HEAD` and `INPUT_FINGERPRINT` match the current invocation. After a new commit or working-tree change, the fixer can target an older CI run and persist mismatched evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-wire: Accept `RUN_ID` from ship state or `fixer-status.env` only when the sidecar’s identity fields match the current invocation; otherwise ignore the cached value and re-resolve from PR checks (or fail closed with `operator-bail`).


### FINDING_2: PR-only merge-result path is validated before run-ID resolution
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: PR-only child invocations validate `--bgjob-result-env` against the PR-derived path, then resolve a numeric run ID and write the result to a different run-derived path. The bgjob consumer can therefore read an empty or stale merge-result file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Resolve the run ID before deriving and validating the merge path, or reject PR-only child invocations until the caller restarts with the resolved identity.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_3: Child-lane behavioral tests are substantially missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: Existing tests cover little beyond registration, help, or prompt rendering. Identity binding, PR-only run-ID resolution, evidence handling, typed outcomes, launcher dispatch, persistence ordering, stale-result rejection, partial failures, cwd restoration, and closed-failure behavior can regress without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Add injected-runner and launcher-fake tests that call ci_fixer_lane.main() across valid and rejected protocol paths.
  - From dyn-dyn-bgjob-wire: Add injected-runner unit tests in `test_ci.py` that exercise the full child contract listed in the plan (identity validation, evidence paths, launcher dispatch, persistence ordering, and closed-failure vs typed-bail exits).


### FINDING_4: Step 8 shell harness lacks bgjob routing coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: The shell harness is largely static and does not exercise bgjob start, rejoin, `WAIT`, `DONE`, `DEAD`/missing-registry recovery, stale identity rejection, merge/status disagreement, symlink rejection, or typed merge-result forwarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Create an isolated fake CLI/bgjob harness that executes the complete routing and rejection matrix and verifies the deterministic merge-result path forwarding.
  - From dyn-dyn-bgjob-wire: Extend the harness with isolated fake CLI/bgjob stubs (as the plan specifies) and assert argv/env routing for start, rejoin, `WAIT`, valid `DONE`, missing results, identity mismatch, and merge/status disagreement paths.


### FINDING_8: Failed CI-log collection can be treated as fixer evidence
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: When `gh` CI-log collection fails due to authentication, network, or other errors, the nonempty diagnostic or pointer may be persisted as raw evidence and permit a repository-mutating fixer launch. Raw fallback should be limited to successfully collected logs whose digest persistence failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Allow raw fallback only for successfully collected logs whose digest persistence failed; persist operator-bail for error, empty, or unhealthy evidence states.


### FINDING_9: Completion-time status and merge files are not symlink-safe
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Completion-time reads do not revalidate that status and merge-result files remain regular, non-symlink files. Replacing the status file with a symlink after initial validation can redirect reads while still passing field comparisons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: At read time, canonicalize and containment-check both files and require non-symlink regular files before parsing them.


### FINDING_10: Wrapper ancestor symlinks can redirect filesystem operations
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Checking only the terminal `IMPLEMENT_TMPDIR` path does not prevent a symlinked ancestor from redirecting `mkdir -p` or sidecar deletion outside the intended session root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Canonicalize and containment-check the tmpdir and every derived path, reject symlinked ancestors, and re-check immediately before mkdir or rm.


### FINDING_12: Dispatch integration tests do not execute the wrapper protocol
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Dispatch tests only statically inspect the wrapper; subprocess behavior for re-entry, stale results, typed routing, and merge-result environment handling is unverified at the integration boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add subprocess fixtures driving step-8-ci-fixer.sh with stubbed bgjob envelopes and pre-seeded handoff files asserting stdout KVs per scenario.


### FINDING_14: Persistence ordering can leave status, merge, and rounds inconsistent
- **Reviewer(s)**: dyn-dyn-bgjob-wire
- **Severity**: major
- **Concern**: `_persist` writes status and bgjob merge-result artifacts before appending `fixer-rounds.tsv`. If the rounds write fails, durable artifacts advertise a completed attempt while the rounds file omits it, allowing duplicate or incorrect resumed work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-wire: Write rounds first to a validated temp file and fsync/rename only after merge/status byte-equality checks succeed, or roll back status/merge on any rounds write failure so durable artifacts stay mutually consistent.
