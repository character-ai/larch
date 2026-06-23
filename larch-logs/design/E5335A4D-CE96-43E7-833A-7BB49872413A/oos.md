### OOS_1: Stale Gate B severity cross-reference after rubric migration
- **Description**: Stale Gate B severity cross-reference after rubric migration. Scenario: `plan-review.md` still tells readers to use `approval-gates.md` **Severity classification rubric** for Gate B presentation after that section becomes a Python-owned contract. Agents loading Step 3 guidance may follow the wrong severity source.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:69
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Stale Gate B severity pointer after rubric migration
- **Description**: Stale Gate B severity pointer after rubric migration. Scenario: Line 69 still sends readers to `approval-gates.md` **Severity classification rubric** for Gate B presentation after that section becomes a Python contract. Step 3 docs can mislead maintainers about the authoritative surface.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/references/plan-review.md:69
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: SECURITY allowlist note omits `preview --variant gate-b`
- **Description**: SECURITY allowlist note omits `preview --variant gate-b`. Scenario: The security allowlist paragraph lists step2b/step3/gatec preview variants but not the new gate-b variant the plan adds. Operators auditing tmpdir validation coverage may miss the new early-exit path.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:196
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Golden test for unfiltered rejected context at Gate B preview
- **Description**: Golden test for unfiltered rejected context at Gate B preview. Scenario: The plan tests rejected/OOS presence but not ledger-filter regression. A future refactor could accidentally wire `emit_rejected_findings` into gate-b preview without a targeted test failing.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_plan_review.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: Stale Gate B severity cross-reference after rubric migration
- **Description**: Stale Gate B severity cross-reference after rubric migration. Scenario: After `approval-gates.md` drops orchestrator rubric prose, plan-review.md still points Gate B presentation at `approval-gates.md` **Severity classification rubric**, which will misroute maintainers even though runtime Gate B will use Python KVs.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:69
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: Stale Gate B severity precedence pointer still cites approval-gates.md Severity classification rubric after migration.
- **Description**: Stale Gate B severity precedence pointer still cites approval-gates.md Severity classification rubric after migration.. Scenario: Readers of plan-review.md may follow a dead cross-reference; Step 3.5 does not load that file, so this does not block the per-round-approval Gate B port.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:69
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: SECURITY.md preview allowlist note lists step2b/step3/gatec but not the new gate-b variant.
- **Description**: SECURITY.md preview allowlist note lists step2b/step3/gatec but not the new gate-b variant.. Scenario: Security reviewers may miss that gate-b shares the same tmpdir validation and warning-only invalid-path contract as other preview variants.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: security
- **Location**: SECURITY.md:196
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

