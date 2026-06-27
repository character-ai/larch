### OOS_1: [SCOPE-REDUCTION] Split `_handle_step2b_drafter_success` only if regen adds helper baseline rows
- **Description**: [SCOPE-REDUCTION] Split `_handle_step2b_drafter_success` only if regen adds helper baseline rows. Scenario: Even with main under cap, this helper still folds preview, scout logging, postplan rc branches, rc11 pause, dialectic promotion, and action emission (~80 lines). Mechanical extraction may move C901/PLR091* debt from `step2b_drafter_main` into a new baseline row without changing runtime behavior, leaving the escalation goal half-met.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_lifecycle.py:3803-3887
- **Phase**: design



