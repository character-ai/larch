### OOS_1: [OUT_OF_SCOPE] stale gitleaks allowlist entries for deleted test fixtures
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.gitleaks.toml` still allowlists deleted fixture paths (`scripts/test-relevant-checks-helper-failure.sh` at lines 13 and/or 106). No current functional impact; a future reintroduced file could contain secret-shaped data without gitleaks reporting it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Remove the stale allowlist entry
  - From cursor-specialist-testing-output.txt: Remove dead allowlist path


