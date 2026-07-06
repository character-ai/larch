### FINDING_2: [OUT_OF_SCOPE] pre-commit trigger coverage misses authority-only edits
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-topology
- **Severity**: minor
- **Concern**: The local pre-commit trigger set does not rerun `lint topology-rule-paths` when only authority-file paths change, so authority-only edits can miss local feedback and defer failure to CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add authority paths from topology.tsv to the hook files list or use a broader trigger.
  - From cursor-specialist-edge-cases: Add authority paths to hook files or document manual lint topology-rule-paths for authority-only edits.
  - From cursor-specialist-testing: Add runtime_authority paths or a broader topology validation trigger set.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] authority-value substring checks are too loose
- **Reviewer(s)**: dyn-dyn-topology
- **Severity**: minor
- **Concern**: The authority-value check relies on plain substring containment, so incidental prose can satisfy the lint even when the real authority token is absent.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] gh body guidance lacks lint cross-link
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: G-Sec-3 gh-body guidance no longer points authors to the `gh-body-inline` lint or `BASH_AUTHORING.md`, so readers can miss the mechanical enforcement when adding new `gh` body call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a G-Sec-3 deviate pointer to BASH_AUTHORING.md §4 and lint gh-body-inline.
  - From cursor-specialist-testing: Add a one-line pointer to python3 python/cli.py lint gh-body-inline in BASH_AUTHORING.md.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] learn_from_bugs skips legacy `.claude/rules`
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `learn_from_bugs` no longer scans legacy `.claude/rules` guidance in target repos, so dedup can miss existing advice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document manual legacy-rule checks or add an optional legacy-rules scan flag.
  - From cursor-specialist-testing: Document the intentional gap or add optional legacy-rules scanning behind a flag.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] symlinked authorities are rejected
- **Reviewer(s)**: dyn-dyn-topology
- **Severity**: minor
- **Concern**: `check_topology_rule_paths` rejects symlinked authorities even though the renderer accepts symlink targets that resolve to regular files, so the two surfaces can diverge.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

