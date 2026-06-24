### OOS_1: [SCOPE-REDUCTION] PHASE_RESULT_ENV_ALLOW_KEYS expanded for stdout-only OOS_SKIP_BREADCRUMB and SETTLE_NEXT_ACTION with no persistence writer
- **Description**: [SCOPE-REDUCTION] PHASE_RESULT_ENV_ALLOW_KEYS expanded for stdout-only OOS_SKIP_BREADCRUMB and SETTLE_NEXT_ACTION with no persistence writer. Scenario: Neither step5b_prepare_main nor design-step35-settle.sh persists these keys through phase_driver_write_result_env; they are stdout-only dispatch rows. Adding allowlist entries plus test_design_lifecycle.py coverage widens the result-env contract without execution-path benefit.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/design_lifecycle.py:47-48
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] Plan does not update the Step 5b .completed/step-5b completion paragraph
- **Description**: [SCOPE-REDUCTION] Plan does not update the Step 5b .completed/step-5b completion paragraph. Scenario: The skip-already-filed-sentinel without-annotate path now writes .completed/step-5b at prepare; line 813 still describes only generic prepare skip paths and annotate ownership without the new conditional. Operators may misread when annotate defers completion.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:813
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] PHASE_RESULT_ENV_ALLOW_KEYS expanded for stdout-only OOS_SKIP_BREADCRUMB and SETTLE_NEXT_ACTION with no persistence writer
- **Description**: [SCOPE-REDUCTION] PHASE_RESULT_ENV_ALLOW_KEYS expanded for stdout-only OOS_SKIP_BREADCRUMB and SETTLE_NEXT_ACTION with no persistence writer. Scenario: The plan adds both keys to PHASE_RESULT_ENV_ALLOW_KEYS plus test_design_lifecycle.py coverage, but neither Step 5b prepare nor design-step35-settle.sh persists them through phase_driver_write_result_env. They are emitted on wrapper stdout only.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:47-48
- **Phase**: design



