### OOS_1: Render-cost allowlist still whitelists `scripts/test-design-structure.sh`
- **Description**: Render-cost allowlist still whitelists `scripts/test-design-structure.sh`. Scenario: The harness grep allowlist includes the retired design structure path; after deletion the render-cost callsite lane fails until the allowlist is edited
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-render-cost-line-callsites.sh:16
- **Phase**: design

### OOS_2: Anti-pattern #3 cites nonexistent assert_wrapper_pause_before_work
- **Description**: Anti-pattern #3 cites nonexistent assert_wrapper_pause_before_work. Scenario: The harness no longer defines assert_wrapper_pause_before_work (only a stale name in SKILL.md). Retargeting to pytest without rewriting the prose leaves misleading enforcement guidance.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:78
- **Phase**: design

### OOS_3: Seven focused-target doc rows are overstated
- **Description**: Seven focused-target doc rows are overstated. Scenario: Plan requires updating seven docs/linting.md focused-target entries, but only the alias target has a dedicated table row today. Adding six redundant rows expands doc churn without changing harness behavior.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: docs/linting.md:404
- **Phase**: design

### OOS_4: Review SKILL.md 200-line ceiling lacks an explicit named-test callout in FILES
- **Description**: Review SKILL.md 200-line ceiling lacks an explicit named-test callout in FILES. Scenario: Deleting scripts/test-review-structure.sh removes the wc -l guard unless it is re-homed. The plan generic specialized-test wording may still cover it during parity work, but the FILES list does not name this assertion.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-review-structure.sh:60-62
- **Phase**: design

