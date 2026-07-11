### FINDING_15: [OUT_OF_SCOPE] Architectural guideline and invariant parsers remain fence-blind
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: `parse_guideline_entries` and `parse_invariant_entries` still apply heading regexes across `splitlines()` without fence-state gating. These pre-existing rows are covered by the baseline and are outside this branch’s lint scaffolding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Follow-up: reuse _balanced_fence_line_indices in architectural guideline parsing
  - From dyn-dyn-ast-lint-precision: Fixing the parsers per G-Md-3 (reuse `_balanced_fence_line_indices`) would shrink baseline debt but is pre-existing scope outside this branch’s lint scaffolding.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Commit-time tmpdir-pointer invariant lacks mechanical backing
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The I-Commit-1 invariant still lacks a commit-time tmpdir-pointer scan in this change, so run-log fields could retain session-tmpdir pointers until follow-up work lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Implement commit-time tmpdir-pointer scan in a follow-up issue
  - From cursor-specialist-testing: Track follow-up work to implement the invariant’s mechanical backing.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] OOS markdown counter remains fence-blind
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The OOS markdown counter still uses a fence-blind heading regex. This is pre-existing behavior baselined by the markdown-heading-fence-state lint and is outside the current scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Follow-up: add fence-state gating to _count_non_security_markdown


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_18: [OUT_OF_SCOPE] New lints lack standalone required CI checks
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new lints are not standalone required CI status checks; CI relies on `py-lint-checks-fast` and pre-commit. This is accepted by the plan or should be handled separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept per plan, or add required jobs in a separate change.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Narrow unreachable detector has no matching production debt
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: `_final_verdict` contains a reachable second branch and is not the dead duplicate targeted by #6153. The empty baseline is consistent with the detector’s current narrow scope rather than evidence that all production dead branches are covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: The empty `python/unreachable-branch-baseline.json` is consistent with the current narrow detector not matching production code, not evidence the lint is green on all dead branches.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Baseline write mode can grow rows
- **Reviewer(s)**: dyn-dyn-ast-lint-precision
- **Severity**: minor
- **Concern**: Check mode rejects stale baseline rows, but `--write` can add newly discovered identities and lacks a shrink-only assertion. This is a maintainer-process risk matching sibling lints, not a runtime correctness defect in the gate code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ast-lint-precision: Aligning regen with `test_lint_tempfile_dir.py::test_write_preserves_reasons_and_shrinks_obsolete_rows` would harden the ratchet; current behavior matches sibling lints and is maintainer-process risk rather than a runtime correctness defect in gate code.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
