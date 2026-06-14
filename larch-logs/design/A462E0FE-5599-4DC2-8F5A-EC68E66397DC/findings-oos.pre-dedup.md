### OOS_1:
- **Description**: When `.step3-review-result.env` is a symlink, `WARN=` from the loop stdout capture is not replayed on wrapper stdout because replay is gated on `_step3_primary_regular`. Scenario: Persist-failure `WARN=` stays invisible to the orchestrator on the symlink path even though `execution-issues.md` logging is added; harder to correlate the background-task failure
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:430-442
- **Phase**: design

### OOS_1:
- **Description**: Diagnostic symlink safety assertion is extra harness surface not tied to the reported bug. Scenario: The predictable diagnostic-path symlink check does not validate persist-fail observability, wrapper handoff, or stdin redirection from issue #4277. It adds maintenance surface to the loop harness only.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:125-127
- **Phase**: design

