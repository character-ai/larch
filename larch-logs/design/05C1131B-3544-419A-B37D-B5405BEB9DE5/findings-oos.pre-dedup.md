### OOS_1:
- **Description**: [OUT_OF_SCOPE] New SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_CMD env duplicates SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH. Scenario: Extra override surface without a required behavior change for the port
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/plan_scout.py
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Plan enumerates 80+ named pytest cases inline. Scenario: Parity is required, but the plan body duplicates what `scripts/test-launch-review.sh` sections already define; the spec risks review churn without adding behavior
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:218-321
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] New `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_CMD` env surface alongside `_SH`. Scenario: Minimum cutover only needs the default argv prefix retarget; a second env var plus optional `_SH` compat expands configuration surface unless an operator need exists
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/plan_scout.py:464
- **Phase**: design

