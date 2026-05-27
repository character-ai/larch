### [Plan Review] FINDING_3

### FINDING_3: expected_judges contract is undefined
- **Reviewer(s)**: Cursor-dyn-refactor-equivalence, Codex-dyn-refactor-equivalence
- **Severity**: important
- **Concern**: The plan introduces `voter_coverage_emit_degraded_warning_if_needed(effective_judges, expected_judges)` without defining `expected_judges`, risking unset-variable failures or changes to the fixed three-judge panel semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-refactor-equivalence: Specify the minimum-change contract explicitly: keep expected_judges=3 in dispatch-plan-voters.sh or pass literal 3 to the helper, and preserve the effective judge condition status != failed && parse_rate_status != NOT_SUBSTANTIVE && -s path.
  - From Codex-dyn-refactor-equivalence: Specify the minimum-change contract explicitly: keep expected_judges=3 in dispatch-plan-voters.sh or pass literal 3 to the helper, and preserve the effective judge condition status != failed && parse_rate_status != NOT_SUBSTANTIVE && -s path.

