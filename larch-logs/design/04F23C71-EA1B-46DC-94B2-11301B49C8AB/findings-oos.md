### OOS_1: Persist-failure path still leaves the final report silent despite acceptance wording asking for a visible explanation when a current-HEAD note cannot be delivered
- **Description**: Persist-failure path still leaves the final report silent despite acceptance wording asking for a visible explanation when a current-HEAD note cannot be delivered. Scenario: The plan documents fail-open behavior (edge case line 204): when `persist_dropped_note_notice` fails, callers return `""` and only log warnings. That matches round-4 accepted fail-open intent but not the literal acceptance criterion for infra failures (read-only/full tmpdir).
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: summary-final.md
- **Phase**: design



