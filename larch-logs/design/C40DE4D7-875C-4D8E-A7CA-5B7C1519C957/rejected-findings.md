### [Plan Review] FINDING_2

### FINDING_2: Teardown traps can kill the recycled owner without rechecking identity
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The cleanup traps can still tear down the recycled PID by raw PID/PGID after the scenario has passed, without revalidating that the process is still the same owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Track the recorded identity for each started process and check it again in teardown, or exclude the recycled-owner PID from trap cleanup.


### [Plan Review] FINDING_3

### FINDING_3: Owner-death wait budget may be too short
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The owner-death scenario needs three consecutive owner-validation failures before the grace timer starts, so a wait budget that only covers grace plus one poll can still flake on slower runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin an explicit wait budget in scenario 2: at least three poll intervals at the overridden poll rate, plus the overridden grace window, plus small slack; fail with diagnostics if BGJOB_RC=orphaned is not observed in time


### [Plan Review] FINDING_4

### FINDING_4: Invalid timing overrides should fail before `STARTED`
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The new test-only override helpers only read env inside the monitor loop, so a malformed override can surface after the job has already been registered and `STARTED` has been printed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a preflight parse before the child registers or prints STARTED, while keeping the call-time reads in `_check_owner_validation` and `_monitor`.


