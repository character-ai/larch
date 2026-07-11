### FINDING_1: Fresh Step 8 re-author-required results retry instead of terminating
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The fresh-child completion switch omits `emit-reauthor`. A valid `re-author-required` result falls through to the retry/fail-closed path, launches attempt 2, and can avoid the intended reassessment handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add an emit-reauthor branch that emits the terminal envelope and exits 0.
  - From cursor-specialist-edge-cases: Add emit-reauthor branch that emits terminal stdout and exits without retry.
  - From codex-specialist-edge-cases: Add an emit-reauthor branch that emits the terminal envelope and exits 0.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
