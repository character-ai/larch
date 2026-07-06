### FINDING_3: [OUT_OF_SCOPE] NEVER #8 still documents a stale deny-then-probe fallback
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The implement NEVER #8 fallback still assumes task-output reads are denied before the sentinel probe, but the hook no longer follows that path, so the prose can push operators into an unnecessary probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove or narrow the denied-read recovery paragraph in NEVER #8.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### FINDING_4: Lawful classification-yield turns should not count against no-progress
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Silent-yield turns that are already allowed after a classification Read still increment the no-progress counter, so repeated spurious notifications can trip the 5-turn breaker before the background task finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Exempt lawful classification-yield turns from the counter, reset on empty/whitespace-only classification, or document and test a higher threshold for design Step 3.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_13: [OUT_OF_SCOPE] Implement premature recovery remains out of scope here
- **Reviewer(s)**: dyn-dyn-bg-wait
- **Severity**: minor
- **Concern**: `/implement` Steps 3 and 5 still use notification-only premature recovery, but this branch intentionally scoped Fix A/B to `/design` only, so the implement path is left unchanged by design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

