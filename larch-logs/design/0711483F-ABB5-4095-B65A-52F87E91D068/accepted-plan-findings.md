### FINDING_1: Gate C persist dispatch is underspecified
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The Gate C prose lists persist branches but does not say when to choose clean vs remediated-violations vs absent/invalid. That leaves an approval run able to persist a clean invariant assessment even after violations were discovered and remediated, which would drop the required audit trail for the invariant check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Mirror the guideline persist dispatch shape: **Clean** only when invariants are present with parsed non-empty content and no violation assessment was required; **Remediated-violations** when violations were identified and the remediation loop produced a clean plan (write a short summary to "$DESIGN_TMPDIR/architectural-invariant-assessment.input.sidecar", then persist with --assessment-file); **Absent, invalid, or present-but-empty** when read_invariants().status is not present or parsed content.strip() is empty (no assessment flags). Pin the dispatch prose and branch order in scripts/test-design-structure.sh alongside the existing persist-command pins.`


