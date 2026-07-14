### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:178-214
- **Concern**: Plan fixes only one issue-view caller, leaving the other issue view/edit/close raw-argv callers in the scoped contract-unification work, contrary to G-Fix-1 and G-Py-7. Scenario: The adoption goal remains incomplete and the raw-argv failure and retry divergence persists at sibling callers
- **Proposed resolution**: Enumerate and repoint every issue view/edit/close caller assigned to this child, or explicitly track the remaining callers before completing the feature



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_gh_argv_literal.py:27-41; .pre-commit-config.yaml:335-341
- **Concern**: The adoption-ratchet lint scans only python/. Scenario: This plan removes the current raw argv in skills/ but a future skills/**/*.py violation would pass lint and pre-commit
- **Proposed resolution**: Extend lint and pre-commit scope to production skills/**/*.py while retaining fixture suppression and add coverage for a rejected skill file



