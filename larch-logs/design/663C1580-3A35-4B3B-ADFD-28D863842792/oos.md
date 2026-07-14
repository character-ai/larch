### OOS_1: `regen-complexity-baseline` still documents `--write` as the regeneration source of truth
- **Description**: `regen-complexity-baseline` still documents `--write` as the regeneration source of truth. Scenario: After Piece 1 blocks `--write` on the migrated committed baseline, operators and ci-fixer guidance that point at `make regen-complexity-baseline` get exit 2 until Piece 2 lands, with no Makefile note about the temporary restriction.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: Makefile:89-92
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

