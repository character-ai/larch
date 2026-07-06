### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Stop-block fallback can misreport zero turns
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-hook-state
- **Severity**: minor
- **Concern**: After the Stop direct-block path fires, `scripts/hook-no-progress-guard.sh` resets `no-progress-turns.count` and leaves `no-progress-circuit-breaker-armed` set. The later `UserPromptSubmit` fallback then reads the counter and can report `0` consecutive turns even though the session just crossed the threshold, which weakens the operator-facing recovery text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-hook-state: Snapshot the bump count into a durable sidecar before resetting the turn counter (for example `no-progress-stop-block-count`), or stop resetting `no-progress-turns.count` until marker release; have UserPromptSubmit prefer that snapshot when `no-progress-stop-block-emitted` or `no-progress-circuit-breaker-armed` is present.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

