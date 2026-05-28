### [Plan Review] FINDING_8

### FINDING_8: Lint tests do not require missing-one coverage for each new env var
- **Reviewer(s)**: Cursor-dyn-linter-coverage-completeness, Codex-dyn-linter-coverage-completeness
- **Severity**: important
- **Concern**: Planned lint tests cover invocation shapes but do not explicitly require one-missing-variable cases for each new required env var. A fixture that omits all new variables as a block would not catch a later regression dropping only one required name.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-linter-coverage-completeness: Specify parameterized missing-one tests for each new variable across the literal, variable-backed, and default-expansion invocation shapes, with the other required unset names present in each fixture.

