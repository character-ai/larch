### OOS_1: External-reviewers doc still instructs launching reviewers with run_in_background
- **Description**: External-reviewers doc still instructs launching reviewers with run_in_background. Scenario: After skill migration the inverse lint allowlists only retained legacy docs. external-reviewers.md remains a loaded operator contract and still teaches notification-era background launches, so degraded-tool guidance can reintroduce the removed primitive outside the linted skills surface.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: docs/external-reviewers.md
- **Phase**: design



### OOS_2: Issue machinery mentions bgjob status for debugging but the plan does not wire /larch:status
- **Description**: Issue machinery mentions bgjob status for debugging but the plan does not wire /larch:status. Scenario: The issue defines bgjob status for /larch:status and debugging. Acceptance does not require it, yet operators have no first-class visibility into live registry rows after abandoning notification waits.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/status/SKILL.md
- **Phase**: design



### OOS_3: Consecutive-bash lint still treats run_in_background as the async-fence escape hatch
- **Description**: Consecutive-bash lint still treats run_in_background as the async-fence escape hatch. Scenario: Once migrated skills stop using run_in_background outside the allowlist, lint_consecutive_bash.py line 208 still exempts any fence containing run_in_background from consecutive-bash rules. New skill prose could reintroduce chained background fences without hitting bg-wait inverse lint.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_consecutive_bash.py:208
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Maintainer sibling doc still documents .bg-wait-active detach/reattach after wrapper migrates to bgjob
- **Description**: [OUT_OF_SCOPE] Maintainer sibling doc still documents .bg-wait-active detach/reattach after wrapper migrates to bgjob. Scenario: Runtime SKILL.md is updated, but editors relying on step-5-review.md will reintroduce retired marker/detach semantics while changing Step 5 wrapper
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-5-review.md
- **Phase**: design



