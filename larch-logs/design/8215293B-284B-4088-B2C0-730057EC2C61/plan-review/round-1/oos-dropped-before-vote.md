### OOS_5: Adapter retries on any non-zero BGJOB_RC
- **Description**: Adapter retries on any non-zero BGJOB_RC. Scenario: The plan retries once after any non-zero BGJOB_RC; Piece 2 usage-error and permanent failed exits are unlikely to succeed on a second identical launch, so the retry adds wall time without improving outcomes without changing terminal fail-closed behavior
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/step-8-assessment.sh
- **Phase**: design

