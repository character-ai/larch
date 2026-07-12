### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Salvage provenance rejects commits with trailing trailers
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: The combined regex and `git %(trailers:key=...)` validation can reject valid salvage commits when another trailer follows `Larch-Salvage-Step`, causing valid fixer salvage to be treated as operator-bailed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Finalize-wrapper harness is not registered in CI
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: CI never executes the changed crash-salvage wrapper cases because the required harness is not registered in a Makefile target or test-harness shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Unreadable commit-body failure is untested
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: A regression could authorize reship after commit metadata reads fail because neither direct dispatch nor crash finalization tests this failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0
