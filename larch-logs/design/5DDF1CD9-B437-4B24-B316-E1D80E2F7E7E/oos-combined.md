### OOS_1: [OUT_OF_SCOPE] Manual ci wait default remains an empty-checks full-timeout path
- **Description**: [OUT_OF_SCOPE] Manual ci wait default remains an empty-checks full-timeout path. Scenario: The plan keeps python/ci.py unchanged, so python3 python/cli.py ci wait with default --empty-checks-grace 0 can still poll a zero-check head until poll-budget-exhausted. This is outside the ship-driver minimum change, but matches the issue's synthetic reproduction path.
- **Reviewer**: Codex-Generic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/ci.py:173-265
- **Phase**: design
