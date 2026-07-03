### OOS_1: SECURITY.md still documents clone identity only via .larch-keepalive CLONE_PATH after marker-local identity becomes the preferred contract.
- **Description**: SECURITY.md still documents clone identity only via .larch-keepalive CLONE_PATH after marker-local identity becomes the preferred contract.. Scenario: Operators and security reviewers reading SECURITY.md will miss embedded marker CLONE_PATH, its keepalive fallback, and unknown-identity fail-closed behavior that the plan adds elsewhere.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: SECURITY.md:222-228
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: SECURITY.md still documents clone scoping only via .larch-keepalive CLONE_PATH
- **Description**: SECURITY.md still documents clone scoping only via .larch-keepalive CLONE_PATH. Scenario: Once markers can embed CLONE_PATH, SECURITY.md would misstate how hook isolation resolves clone identity for operators auditing the threat model.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:222
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

