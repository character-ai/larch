### [Plan Review] FINDING_12

### FINDING_12: Assertion 8b can pass with split, non-equivalent substrings
- **Reviewer(s)**: Codex-dyn-assertion-logic
- **Severity**: important
- **Concern**: Assertion 8b checks two substrings separately even though the invariant requires a single suppression sentence tying failed issue filing to no accepted disposition URL rows in `oos-issues.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-assertion-logic: Pin one exact fixed string or a single-line grep that contains both the suppression phrase and oos-issues NDJSON; make the negative check line-scoped to ISSUES_FAILED>0 plus append accepted disposition URLs


