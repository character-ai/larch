### FINDING_2: Production pragmas can disable the hard ban
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Allowing production literals to use the planned pragma lets violating code bypass the adoption lint, allowing enforcement to decay while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Permit pragma suppression only for explicit test-fixture paths or a reason-bearing fixture allowlist; reject production pragmas and replace the planned production-side suppression test with that rejection case


### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_gh_argv_literal.py
- **Concern**: [SCOPE-REDUCTION] Production pragmas defeat the hard ban. Scenario: The plan explicitly permits and tests a production-side pragma, so a new raw production `["gh", ...]` argv can bypass the required ban with a comment.
- **Proposed resolution**: Restrict suppression to test fixtures under `python/tests/` or an explicit fixture allowlist, and remove production-side pragma support and coverage.


