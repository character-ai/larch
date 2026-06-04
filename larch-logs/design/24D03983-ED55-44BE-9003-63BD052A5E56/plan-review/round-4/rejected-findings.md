### [Plan Review] FINDING_13

### FINDING_13: Negative structure pin is too exact-string dependent
- **Reviewer(s)**: Codex-dyn-test-pin-fidelity
- **Severity**: important
- **Concern**: The planned negative test only checks an exact string, so old bash-default selector semantics could survive with line wrapping or whitespace changes while passing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-pin-fidelity: Use a selector-scoped regex negative, e.g. fail if the Python selector paragraph matches `default[[:space:]]+\`LARCH_SHIP_PR_IMPL=bash\`[[:space:]]+runs[[:space:]]+the[[:space:]]+bash[[:space:]]+contract`.

