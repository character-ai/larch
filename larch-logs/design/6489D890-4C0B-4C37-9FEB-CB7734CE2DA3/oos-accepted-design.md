### OOS_1:
- **Description**: Item 3 makes execution-issues warnings the primary durable diagnostic, but Step 7a still skips `_run_log_flush` when the 7a.r rebase probe fails.. Scenario: On diagram failure plus rebase conflict/failure, enriched warnings and the copied `code-flow-diagram.failure.log` stay in the tmpdir and never reach committed `execution-issues.ndjson` or repo `larch-logs/`. This gap predates the plan; stdout `DIAGRAM_REASON` alone is ephemeral.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/step_7a.py:291-298
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4580
