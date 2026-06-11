### OOS_1:
- **Description**: Stale-reference sweep omits agent-lint.toml cleanup for deleted blocker/issue helper excludes. Scenario: Retired paths remain in dead-script exclude lists and comments after files are deleted
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:122-134
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Harness table omits future test-blocker and test-issue-query discoverability rows. Scenario: Operators lose Makefile target documentation for the new pytest harnesses; CI still runs them via Makefile shards
- **Reviewer**: Cursor-dyn-stale-ref-completeness
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: docs/linting.md:225
- **Phase**: design

### OOS_2:
- **Description**: relevant-checks mapping omits implement-bootstrap-invoke.md sibling contract. Scenario: Editing only implement-bootstrap-invoke.md will not route test-implement-bootstrap-invoke via relevant-checks.sh (invoke .sh and harness .sh are mapped at plan.txt:683-684)
- **Reviewer**: Cursor-dyn-stale-ref-completeness
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap-invoke.md
- **Phase**: design

