### OOS_1: Cross-repo mining still scans cwd enforcement surface while filing to `REPO`
- **Description**: Cross-repo mining still scans cwd enforcement surface while filing to `REPO`. Scenario: Even with `--repo` passthrough to `/issue`, `prepare --root "$PWD"` indexes guidelines, invariants, and lints from the checkout cwd. A plugin-checkout run that mines another repo can auto-file adoption issues describing the wrong enforcement surface.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/learn-from-bugs/SKILL.md:42-57
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

