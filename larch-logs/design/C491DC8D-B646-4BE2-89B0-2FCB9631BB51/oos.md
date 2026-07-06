### OOS_1: A5 extends the `runner.run(["gh", ...])` lint only; `issue_create.py` gh access is mostly `proc.run(["gh", ...])`, which stays outside the new AST rule even if some call sites are migrated.
- **Description**: A5 extends the `runner.run(["gh", ...])` lint only; `issue_create.py` gh access is mostly `proc.run(["gh", ...])`, which stays outside the new AST rule even if some call sites are migrated.. Scenario: The code half of A5 can migrate individual sites, but the lint half will not prevent new `proc.run(["gh", ...])` bypasses in issue tooling unless a follow-up widens the rule family.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/issue_create.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] proc.run gh modules outside the A5 migration list remain untimed and lint-exempt
- **Description**: [OUT_OF_SCOPE] proc.run gh modules outside the A5 migration list remain untimed and lint-exempt. Scenario: audit_runs.py, combine_issues.py, deps_audit.py, issue_block.py, and release/* still call proc.run(["gh", ...]) but are absent from the plan; A5 lint targets runner.run only, so hung-read risk and bypass lanes persist outside gh.py
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/issue/audit_runs.py:335-1112
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

