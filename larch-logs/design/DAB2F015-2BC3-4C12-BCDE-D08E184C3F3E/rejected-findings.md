### [Plan Review] FINDING_4

### FINDING_4: Plan omits required SECURITY.md update for digest artifact
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The PR adds a new mode-0600 digest derived from check output and changes orchestrator guidance from reading `REDACTED_LOG_FILE` first to reading `DIGEST_FILE` first, but `SECURITY.md` would still document only the old redacted-log artifact and consumer rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add SECURITY.md to the firm plan and update the relevant-checks captured logs paragraph to state that failed runs may also write a bounded DIGEST_FILE built only from the redacted log, consumed before REDACTED_LOG_FILE, with raw LOG_FILE still forbidden.


