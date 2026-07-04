### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: `--read-result-env` can bypass detached reattach state
- **Reviewer(s)**: dyn-dyn-signal-lifecycle
- **Severity**: important
- **Concern**: The `--read-result-env` entrypoint normalizes status before detached-marker handling, so recovery can observe `missing` while a detached loop is still running and has not yet persisted its result. That can bypass the reattach contract and trigger a second full Step 3 launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-signal-lifecycle: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

