### OOS_1:
- **Description**: Plan names override env `CHECK_DIRTY_TREE_SH`; runtime override is `REVIEW_CORE_CHECK_DIRTY_TREE_SH`. Scenario: Misdocumented override name can break test stubs during cutover
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:88
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Drop the pre-deletion bash harness parity gate once pytest passes. Scenario: Old harnesses exercise retired bash after CLI cutover; they do not prove the new Python entrypoints
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:919-930
- **Phase**: design

