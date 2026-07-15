### FINDING_1: [OUT_OF_SCOPE] Substring-based fact invalidation can hide unreachable branches
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `drop_names` uses substring matching on AST dumps, so assigning to a short name can incorrectly invalidate facts for longer names and suppress valid findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Uncertain scans omit later class methods
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-occurrence-baseline
- **Severity**: minor
- **Concern**: When path state is uncertain, `_scan_block` does not scan methods in later `ClassDef` nodes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-occurrence-baseline: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Missing required baselines are accepted on clean scans
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A missing unreachable-branch occurrence baseline produces a successful clean scan instead of failing as the legacy rule did.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_7: [OUT_OF_SCOPE] Equivalence test documentation is stale
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The equivalence test module docstring still describes the unreachable-branch implementation as a legacy `scan_file`-only path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Nested functions inside conditional subtrees are skipped after uncertainty
- **Reviewer(s)**: dyn-dyn-occurrence-baseline
- **Severity**: minor
- **Concern**: When path state is uncertain, `_scan_block` skips `ast.If` subtrees, so functions defined only inside such a subtree are not scanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-occurrence-baseline: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Equivalence coverage omits occurrence identity fields
- **Reviewer(s)**: dyn-dyn-occurrence-baseline
- **Severity**: minor
- **Concern**: The equivalence adapter omits `pattern_name` and occurrence fields and compares only path, line, rule ID, and message, so identity drift between the adapter and engine-backed CLI is not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-occurrence-baseline: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
