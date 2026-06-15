### OOS_3:
- **Description**: [OUT_OF_SCOPE] Issue audit for other client-dead-weight files is only partially reflected in cleanup patterns. Scenario: Makefile and parallel-tests.py are deleted but other cone-shipped dev-only root configs (.pre-commit-config.yaml, .markdownlint.json, .markdownlintignore, agent-lint.toml, .agnix.toml, .gitleaks.toml) remain in cache after /upgrade-larch; clients still carry CI/lint dead weight though runtime works
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .pre-commit-config.yaml:1 / .markdownlint.json:1 / agent-lint.toml:1 / .agnix.toml:1 / .gitleaks.toml:1
- **Phase**: design

