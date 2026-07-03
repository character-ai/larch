### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Matching ledger `deep_verdict` is now reachable for `NEEDS_DEEP` bundles
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The matching-ledger `deep_verdict` path is reachable for `NEEDS_DEEP` bundles, which matches the reported production bug shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Fallback mechanical verdict is reachable on ledger miss
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: If `_record_for_bundle` misses because of a hash or `fix_sha` mismatch, the fallback `bundle.mechanical_verdict` branch is now reachable for `NEEDS_DEEP` bundles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

