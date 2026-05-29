### FINDING_18: `SECURITY.md` lacks `/cleanup` trust-boundary documentation after retention redesign
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` (around line 239) lacks a `/cleanup` trust-boundary paragraph after the retention redesign. Auditors may assume old singleton/keepalive protections still apply to session tmpdir deletion. Add a concise `/cleanup` section covering concurrent runs, retention days, depth-5 scan, and session-tmpdir sensitivity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


