# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale result envs can satisfy reattach too early
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: `await_loop_identity_main` / reattach completion can treat any pre-existing `STEP3_REVIEW_LOOP_STATUS` as success, including stale envelopes from a prior round or the missing-pid path before the current detached loop has actually flushed a new result. That lets resume normalize an old completed status and exit while the live loop is still running. Freshness needs to be tied to the current detach/launch epoch, not just presence of any status file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Traps are armed before loop identity is guaranteed
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Signal traps are installed before `write-loop-identity` succeeds. If TERM/HUP/INT arrives after `_loop_pid` is set but before identity exists, the next entry can start a duplicate review while the original loop is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: Successful reattach leaves detached reviewer processes alive
- **Reviewer(s)**: dyn-dyn-signal-lifecycle
- **Severity**: important
- **Concern**: The successful reattach path normalizes the persisted result and exits without running the tmpdir child sweep that the normal completion path performs, so detached reviewer children can still be running even though Step 3 is considered complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-signal-lifecycle: Address the concern above.


