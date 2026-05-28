### OOS_1:
- **Description**: New lint wired only via `Makefile` / `make lint`. Scenario: Sibling `lint-bare-grep-probe` is in pre-commit and `docs/linting.md`; commit-time / doc drift is possible but optional for minimum change
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: docs/linting.md,.pre-commit-config.yaml
- **Phase**: design

### OOS_2:
- **Description**: No pre-commit hook or `docs/linting.md` row for the new lint (unlike `lint-bare-grep-probe`). Scenario: `scripts/relevant-checks.sh` only runs configured pre-commit hooks; authors relying on relevant-checks alone may not see new violations until `make lint`/CI
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .pre-commit-config.yaml:166-168 / docs/linting.md:20
- **Phase**: design

