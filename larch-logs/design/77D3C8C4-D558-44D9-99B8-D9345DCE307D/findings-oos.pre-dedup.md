### OOS_1: [OUT_OF_SCOPE] Persist findings-oos.md at session root when composing the attributed ballot for run-log parity
- **Description**: [OUT_OF_SCOPE] Persist findings-oos.md at session root when composing the attributed ballot for run-log parity. Scenario: progress_report and SECURITY allowlists reference findings-oos.md but the Python driver no longer writes it; omitting the write does not break voting but leaves round artifacts harder to audit from committed logs
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/plan_review_round.py:423-459
- **Phase**: design



