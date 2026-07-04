# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: active-leg publish can fail silently
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `_publish_active_leg_record` can skip persisting `.active-leg.json` when the launch-time process-identity probe fails or is unreadable, so later owner cleanup has nothing to target and a live leg can keep running after dispatcher death.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_3: Step 3 loop identity can race process-group setup
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Step 3 can record loop identity before the child has a stable process group, or fail to publish a usable sidecar when the initial `ps` probe loses the race, and the path has no behavioral coverage to catch the regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Retry ps capture briefly after `_loop_pid=$!` or re-read identity in teardown when sidecar is missing but pid is set.
  - From codex-specialist-correctness: Write the sidecar from the child after setsid or wait until os.getpgid(pid) equals pid before recording.
  - From cursor-specialist-testing: Add pytest for write_loop_identity_main and teardown_loop_identity_main; extend test-design-step3-review.sh with plan-listed behavioral checks.
  - From codex-specialist-testing: Retry until pgid equals the loop pid or write identity in the child after setsid, and add a regression test for the transition.


### FINDING_4: descendant escalation can hit recycled PIDs
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Descendant PIDs are escalated after a grace window without revalidating identity, and a reaped child can let a recycled PID or PGID receive the later SIGKILL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Revalidate descendant identity before per-PID escalation or only signal descendants that still belong to the validated target group/tree.
  - From codex-specialist-correctness: Skip SIGKILL once the process has exited or validate identity before escalation.
  - From codex-specialist-edge-cases: Use killpg only or snapshot and revalidate each descendant pid, pgid, start time, and command before direct signals.


### FINDING_6: kill logs need redaction
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Kill audit logs persist raw command lines, so session artifacts can leak argv secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Redact all KillLogEvent string fields before JSON serialization and test token redaction.


### FINDING_7: owner cleanup can leave children alive
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: When the leader PID is gone, owner cleanup can unlink the active-leg record without proving the rest of the process group is dead, leaving live children behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Validate by live process-group members for owner-token-matching records, or retain the record until safe cleanup is possible.
  - From cursor-specialist-testing: Add integration test: published record, no finally clear, owner-token kill-active-leg validates and consumes record.


