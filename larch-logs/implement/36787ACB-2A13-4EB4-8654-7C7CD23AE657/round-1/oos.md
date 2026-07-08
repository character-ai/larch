### FINDING_1: [OUT_OF_SCOPE] step7a launch test misses env-based owner fallback
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The Step 7a bgjob launch test mocks `_run_cli`, so the env-based owner fallback is never exercised on the launch path. A regression that breaks owner resolution while keeping `--owner-pid` out of argv could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_2: [OUT_OF_SCOPE] owner-pid contract should assert live bgjob argv
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: The owner-pid check only inspects launcher source text, not the executed bgjob start argv. A refactor could leave the `--owner-pid` literal in the file while the live launch command drops it, so the regression would slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Stub python/cli.py bgjob start and assert the emitted argv with LARCH_CLAUDE_PID set and unset


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Step 8 harness should pin owner-pid in dynamic argv
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The Bash harness only captures dynamic argv and does not pin `--owner-pid`, so a runtime-only owner-pid regression could pass the harness even if production launches break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend test-step-8-ship.sh dynamic argv assertions to require --owner-pid "${LARCH_CLAUDE_PID:-$PPID}"


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Step 7a launch test needs sentinel argv assertion
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The Step 7a launch test omits a sentinel argv assertion, so removing `--sentinel` from `_launch_step7a_bgjob` would not fail the test even though completion detection would be broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add assertions that start includes --sentinel and the step-7a terminal path


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] static launcher text should be backed by a runtime smoke test
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The new launcher check only reads shell text; a shell syntax error or dead-code launcher path could still pass if the literal strings remain, so the contract is not exercised end to end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: add one lightweight runtime smoke test for the launcher entrypoint while keeping the static pin


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

