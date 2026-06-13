### OOS_1:
- **Description**: Third inline jq normalize remains after step2 delegates to the design wrapper. Scenario: External coder sidecars get plan-review reserved-slug filtering at Step 2, but Step 5 pre-scout still re-normalizes with a narrower reserved list; duplication stays and paths can diverge again later
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/dispatch-panel.sh:320-387
- **Phase**: design

### OOS_2:
- **Description**: Testing strategy lists make test-parse-drafter-output and make test-launch-codex-drafter though the plan explicitly does not change parse-drafter-output.py or drafter launchers. Scenario: Extra harness runs add churn without covering new code paths for this change
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:39-66
- **Phase**: design

