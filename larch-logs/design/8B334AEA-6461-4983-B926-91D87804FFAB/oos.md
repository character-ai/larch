### OOS_2:
- **Description**: No pre-commit hook or `docs/linting.md` row for the new lint (unlike `lint-bare-grep-probe`). Scenario: `scripts/relevant-checks.sh` only runs configured pre-commit hooks; authors relying on relevant-checks alone may not see new violations until `make lint`/CI
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .pre-commit-config.yaml:166-168 / docs/linting.md:20
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

