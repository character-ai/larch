### FINDING_1: [OUT_OF_SCOPE] Direct larch-run.sh callers can resolve the wrong owner PID
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Direct larch-run.sh invocations do not embed the Claude PID, so callers that skip implement-run-$PPID.sh can fall back to caller-inherited LARCH_CLAUDE_PID or PPID and orphan bgjob after the shell PID goes stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Stale inherited LARCH_CLAUDE_PID can override the embedded launcher PID
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: session_env.py uses ${LARCH_CLAUDE_PID:-pid}, so a stale inherited LARCH_CLAUDE_PID can override the embedded session PID and misassign bgjob ownership even when the launcher filename encodes the correct pid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: If intent changes, prefer embedded launcher PID on mismatch and warn when inherited and embedded values disagree.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Step 5 harnesses do not verify bgjob owner-pid
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The Step 5 review harness and its wrapper test do not assert that bgjob start receives the exported LARCH_CLAUDE_PID as --owner-pid, so an owner-resolution regression could still pass tests while orphaning reviews.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a harness assertion that bgjob start --owner-pid equals the exported LARCH_CLAUDE_PID.
  - From cursor-specialist-testing: Add a harness case that exports only LARCH_CLAUDE_PID and asserts bgjob-start-argv.txt contains the expected --owner-pid value.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

