### FINDING_2: Per-field bounds and sanitization for digest field values
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan caps total digest UTF-8 bytes and allows multiple `check=` record groups, but it does not bound or flatten individual `first_error` (and `first_location`) values. One verbose traceback, pytest dump, or multiline error can consume the entire `CHECKS_FAILURE_DIGEST_MAX_BYTES` budget and set `digest_truncated=true` after the first group, hiding additional failed hooks. Raw newlines or tabs inside field values can also break the line-oriented v1 format and make prompt-side parsing unreliable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define a small CHECKS_FAILURE_DIGEST_FIRST_ERROR_MAX_BYTES (or similar), truncate each first_error before assembling groups, and add a test where one hook emits a huge error yet a second failed hook still appears before digest_truncated=true.
  - From Cursor-Pragmatic: In the digest builder spec, add a small per-field UTF-8 byte cap (for example on first_error and first_location), flatten newlines/tabs to spaces before writing, then apply the existing total CHECKS_FAILURE_DIGEST_MAX_BYTES cap across complete record groups. Add unit tests for multiline traceback input and for two check groups still fitting when errors are large.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Consumer docs still describe REDACTED_LOG_FILE-only failure consumption while DIGEST_FILE becomes primary
- **Description**: Consumer docs still describe REDACTED_LOG_FILE-only failure consumption while DIGEST_FILE becomes primary. Scenario: The relevant-checks paragraph still says orchestrators read only REDACTED_LOG_FILE on failure; the plan leaves docs/linting.md as MAY_UPDATE, so the shipped contract can drift from skill behavior and confuse manual CLI debugging.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:93
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

