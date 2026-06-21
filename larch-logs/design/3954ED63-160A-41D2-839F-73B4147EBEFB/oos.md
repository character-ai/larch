### OOS_1: Heavy-worker `review core` loop omits explicit `--site`
- **Description**: Heavy-worker `review core` loop omits explicit `--site`. Scenario: After FINDING_8’s Python default-site fix, behavior is correct even when `IMPLEMENT_TMPDIR` is exported; adding `--site "review Step 2"` here is consistency-only.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/references/heavy-worker.md:36
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [SCOPE-REDUCTION] Run-summary dynamic-archetype lines are observability not fix mechanics
- **Description**: [SCOPE-REDUCTION] Run-summary dynamic-archetype lines are observability not fix mechanics. Scenario: Stopping implement Step 5 scout regression needs producer manifest plus dispatch gate; summary rendering does not affect whether scout launches
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/final_report.py:149-164
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [SCOPE-REDUCTION] Design-path doc and drafter-warning churn is orthogonal to implement emergency scout regression
- **Description**: [SCOPE-REDUCTION] Design-path doc and drafter-warning churn is orthogonal to implement emergency scout regression. Scenario: Issue repro is /implement --emergency with scout-round1-manifest.json.raw; regular /im already shows dyn-* slots from coder-produced manifests
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:194-205
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Mechanical scout-from-diff helper would avoid new orchestrator JSON authoring burden
- **Description**: Mechanical scout-from-diff helper would avoid new orchestrator JSON authoring burden. Scenario: Requiring the main agent to write scout-coder-manifest.raw.json after coding adds turn complexity and skip risk; issue prefers coder judgment but a Python helper reading git diff plus plan could be smaller
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:Step 2.4
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

