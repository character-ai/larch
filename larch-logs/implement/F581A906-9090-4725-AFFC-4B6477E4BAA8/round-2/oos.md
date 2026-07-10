### FINDING_5: [OUT_OF_SCOPE] Bare SystemExit can be reported as success
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: `fixer_lane_main` maps `SystemExit` with a `None` code to exit status 0, allowing an argument-handling failure to appear as successful bgjob completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Map None to a nonzero usage exit or re-raise before production dispatch.
  - From dyn-dyn-bgjob-wire: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Invariant identity is not revalidated at dispatch
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: The pre-dispatch check verifies regular-file and containment properties but does not re-read and compare identity metadata immediately before launcher dispatch, leaving a TOCTOU window for drift or replacement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Re-read and match `.identity.env` metadata immediately before dispatch when the lane goes live.
  - From dyn-dyn-bgjob-wire: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Launcher invocation omits plan-file context
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-wire
- **Severity**: minor
- **Concern**: The dormant fixer launcher does not pass `--plan-file`, unlike production CI fixer paths, so future Step 8 wiring may launch fixers without plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-wire: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Monitor-state and run-ID-resolution tests are incomplete
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Monitor tests omit required transient and terminal collection states, resolution ambiguity and query failures, malformed jobs, filters, and bounded-timeout behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add offline RecordingRunner cases for every required state and resolution outcome, including timeout behavior without real sleeps.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Step 8 harness is not wired into Makefile test shards
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new shell harness lacks a Makefile target or test-harnesses shard, so default CI may not execute it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a Makefile target and wire it into a test-harnesses shard before production wiring.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
