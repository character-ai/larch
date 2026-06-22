### OOS_1: [SCOPE-REDUCTION] Planned direct unit-test matrix for _count_non_security_blocks largely duplicates python/test_file_oos.py
- **Description**: [SCOPE-REDUCTION] Planned direct unit-test matrix for _count_non_security_blocks largely duplicates python/test_file_oos.py. Scenario: If implementation reuses file_oos._count_non_security_markdown, the listed edge-case tests add churn without new risk coverage on the design path
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:36-40
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Planned legacy FINDING counter matrix exceeds what the design prepare path can exercise
- **Description**: [OUT_OF_SCOPE] Planned legacy FINDING counter matrix exceeds what the design prepare path can exercise. Scenario: _extract_unfiled_blocks in python/design_oos.py:65-78 only extracts ### OOS_ headers before _count_non_security_blocks runs, so legacy ### FINDING_N: fixtures never reach the design counter unless prepare input shape changes. If reusing file_oos._count_non_security_markdown, duplicating the full legacy matrix in test_design_oos.py restates python/test_file_oos.py without new risk coverage.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_design_oos.py:36-40
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Removing the sole awk↔file_oos parity assertion leaves no harness cross-check if design_oos is ported separately from file_oos
- **Description**: [OUT_OF_SCOPE] Removing the sole awk↔file_oos parity assertion leaves no harness cross-check if design_oos is ported separately from file_oos. Scenario: Post-delete regex drift between design prepare and implement gate counters would surface only via split pytest/bash coverage, not one shared fixture loop
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh:219-225
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

