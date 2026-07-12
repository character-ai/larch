### [rejected] FINDING_15

**Rejected subtype:** dismissed (0 YES)

### FINDING_15: Safe OOS discovery lacks regression tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There are no tests covering symlinked or unsafe session run directories during `oos-issues.ndjson` discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (0 YES)

### FINDING_16: Checks-digest discovery lacks symlink tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Checks-digest artifact selection via `safe_child_run_dirs` lacks tests for symlink rejection and single-candidate behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (0 YES)

### FINDING_21: Symlinked manifests now trigger fallback
- **Reviewer(s)**: dyn-dyn-corpus-policy
- **Severity**: major
- **Concern**: Rejecting symlink manifest files changes metadata eligibility, version floors, and ended-at comparisons relative to prior readers that followed regular-file symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-corpus-policy: Either document symlink rejection as an intentional hardening and pin `manifest_candidates=("manifest.json",)` plus `continue_on_empty=False` anywhere symlink fall-through must not occur, or resolve symlink targets with the same containment checks used elsewhere and read the target when it is a regular file.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
