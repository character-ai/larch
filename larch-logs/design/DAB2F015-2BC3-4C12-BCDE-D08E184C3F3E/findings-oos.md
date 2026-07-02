### OOS_1: Consumer docs still describe REDACTED_LOG_FILE-only failure consumption while DIGEST_FILE becomes primary
- **Description**: Consumer docs still describe REDACTED_LOG_FILE-only failure consumption while DIGEST_FILE becomes primary. Scenario: The relevant-checks paragraph still says orchestrators read only REDACTED_LOG_FILE on failure; the plan leaves docs/linting.md as MAY_UPDATE, so the shipped contract can drift from skill behavior and confuse manual CLI debugging.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:93
- **Phase**: design



