### FINDING_4: [OUT_OF_SCOPE] Direct manifest reads in final-report recovery
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-corpus-policy
- **Severity**: minor
- **Concern**: Final-report recovery reads manifests directly instead of using centralized metadata policy, creating potential future divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-corpus-policy: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Duplicate fluff implement architecture observation
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Implement architectural-assessment enumeration duplicates the inline-manifest policy split between fluff design and implement paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Incomplete byte totals on stat failures
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Byte accounting silently ignores per-file stat failures, potentially understating GC totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Inline codex-role manifest metadata
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Codex role-cost analysis reads `manifest.json` directly rather than applying shared symlink and metadata validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Ground-truth policy and plan text diverge
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-corpus-policy
- **Severity**: minor
- **Concern**: Ground-truth preserves legacy empty-manifest stopping behavior while plan prose specifies different continuation semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-corpus-policy: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Lint ratchet has additional known gaps
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The lint ratchet still omits some traversal patterns, leaving future bypasses possible outside the current scanners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_22: Lint fails to track structured corpus provenance
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: The adoption ratchet does not propagate corpus provenance through attributes or structured fields, allowing raw traversal outside the approved owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_25: [OUT_OF_SCOPE] Fail-closed API hides caller wiring errors
- **Reviewer(s)**: dyn-dyn-corpus-policy
- **Severity**: minor
- **Concern**: Mapping containment `ValueError` to “unsafe” hides caller contract mistakes instead of distinguishing invalid API usage from an escape symlink.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-corpus-policy: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
