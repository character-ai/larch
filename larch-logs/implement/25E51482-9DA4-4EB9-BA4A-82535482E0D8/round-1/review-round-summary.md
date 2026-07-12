# Review Round 1

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Malformed duplicate rows preserve invalidated results
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Duplicate malformed rows do not invalidate an earlier parsed result for the same kind, allowing clean output to persist and later lanes to be skipped. Discard invalidated results, keep the kind unresolved, and reject unknown extra rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_5: Claude availability is not session-pinned
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-launch-contract
- **Severity**: major
- **Concern**: The coordinator reads `CLAUDE_BINARY_FOUND`, but normal session setup does not write it. Claude therefore uses live PATH discovery while the other lanes use session-recorded availability, allowing PATH drift to change behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-launch-contract: Probe and persist `CLAUDE_BINARY_FOUND` into `session-env.sh` during implement session setup (mirroring Codex/Cursor), or stop claiming session-recorded Claude availability in docs/coordinator until the writer exists; extend session-env tests and the architectural-assessment availability test to use a real setup-produced session file.


### FINDING_7: Assessment bgjob budget does not cover worst-case lanes
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-launch-contract
- **Severity**: major
- **Concern**: The fixed `5700`-second budget may not cover external-lane wrapper grace periods, retries, and three sequential near-timeout lanes, potentially terminating the waterfall before Claude runs or unavailable results are persisted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-launch-contract: Derive budget from `external_defaults.fixer_lane_budget_sec(config.ARCHITECTURAL_ASSESSMENT_ROLE)` plus explicit wrapper/retry overhead (include the `+60` per external lane and attempt-2 reserve), and add a harness/assertion that three sequential max-timeout lanes still fit under `BUDGET_S`.


### FINDING_8: Missing regression coverage for recursive rematerialization
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no regression test proving that `_HeadDrift` during post-CI-fix persistence causes successful rematerialization rather than an unavailable result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Assessment launcher argv pins are untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Launcher tests do not assert `--sandbox read-only` and `--mode ask`, so regressions could remove required Codex and Cursor safety modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Waterfall failure and stop branches lack tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Planned branches for timeout, all-unavailable, invalid JSON, valid deviation, and stopping lack stub-launcher coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: Preflight failures are misreported as missing sidecars
- **Reviewer(s)**: dyn-dyn-launch-contract
- **Severity**: major
- **Concern**: Codex/Cursor auth or model-argument preflight failures emit diagnostics without `.sidecar`, causing the adapter to report a generic missing-sidecar error instead of the operator-facing failure reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-launch-contract: On preflight short-circuit, write the same minimal `.sidecar` the success path expects (or teach `_shared_launcher_artifact_error` / `SharedReviewLauncher.launch` to accept the preflight `.diag` `FAILURE_REASON` when `LAUNCHER_EXIT!=0`), and add an integration test that Cursor/Codex auth failure surfaces that reason through `_launch_failure_detail`, not the generic sidecar omission string.
