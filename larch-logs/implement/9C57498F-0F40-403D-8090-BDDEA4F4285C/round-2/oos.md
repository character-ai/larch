### FINDING_5: [OUT_OF_SCOPE] Learn-from-bugs errors can surface as tracebacks
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-proposal-lifecycle
- **Severity**: minor
- **Concern**: `LearnFromBugsError` is not converted by the generic CLI dispatch path into a bounded stderr `ERROR` line and stable nonzero exit code, so adoption failures may produce Python tracebacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] `write-state` can overwrite prior proposal history
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `write_state_main` does not reconcile proposals or verify that loaded proposal IDs retain all existing marker IDs. A partial reconciled JSONL could silently erase prior proposal history. Consider failing closed when loaded proposal IDs are not a superset of existing marker IDs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Adoption summaries omit proposed proposals
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `render_adoption_summary` excludes `proposed` entries from pending counts, which can undercount pending work and inflate adoption rates if called before proposal checking. Include proposed entries in pending counts or document that only post-check proposals are valid input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Corrupt markers are mislabeled as missing by `read-state`
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-proposal-lifecycle
- **Severity**: minor
- **Concern**: `read_state_main` reports `FOUND=false` when a present marker fails validation, misrepresenting corrupt state as absent even though other verbs fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-lifecycle: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Marker commits bypass the Python git wrapper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Marker commits use bare git commands rather than the Python git commit wrapper, which may diverge from wrapper lock or guard behavior used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
