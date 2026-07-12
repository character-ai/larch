### FINDING_7: [OUT_OF_SCOPE] Full-tree scan may scale poorly
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Scanning the full tree on every run currently takes several seconds and may increase CI time as the Python tree grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] New fixtures use unrealistic bare markers
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Existing fixtures use emitted HTML-comment markers, but the new positive fixture uses only bare tokens and does not exercise the realistic bypass shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Marker fixtures duplicate grammar literals
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Existing fixtures duplicate plan-marker grammar, creating recurring maintenance when marker syntax changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_10: [OUT_OF_SCOPE] v1 marker literals remain outside ownership
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Pre-existing `larch:plan` v1 `runid=` literals remain outside `issue_wire.py` and are not covered by this ownership policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Direct-import helper limitation is undocumented
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Aliased or direct helper imports are not recognized by the AST walk; this is pre-existing style and outside the implementation-plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Dynamic marker construction is not scanned
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Concatenated or otherwise dynamically constructed marker strings can evade the current constant-only scan; this is speculative hardening beyond plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Helper marker arguments are not asserted
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Wrong-marker helper calls are not rejected by the current checks; stricter keyword validation is explicitly outside implementation-plan scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false
