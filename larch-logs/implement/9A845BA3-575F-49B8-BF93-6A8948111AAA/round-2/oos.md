### FINDING_2: Nonzero log-publish results with recovery metadata are treated as success
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: A nonzero log-publish subprocess result that includes `RECOVERY_BRANCH` falls through as success. The publish path can set `LOG_PUBLISH_COMPLETED=true` and return success despite `PUBLISH_OK=false`, corrupting completion, salvage, and cleanup decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_10: [OUT_OF_SCOPE] Early publish failures do not initialize result-env state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Early rc-5 returns for pre-Step-5b argument failures skip fresh result-env initialization, leaving no current-attempt progress artifact when diagnostics require one.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Publish-tail metadata validation lacks tests
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Terminal-state tests do not cover the new publish-tail `PR_URL` and `RECOVERY_BRANCH` fields. Malformed publish metadata could pass or fail validation without regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Publish-tail tests are not fully represented in shard assignments
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: New publish-tail and reconciliation test node IDs are absent from shard assignments or rely on round-robin behavior, allowing shard balance and coverage mapping to drift until rebalance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Designed-title evidence does not set rename state
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: A `NEW_TITLE` prefixed with `[DESIGNED]` sets `DESIGNED_ADMISSION_READY` but not `RENAMED=true`, so salvage reconciliation requiring rename evidence may miss title-only rename cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Publish-tail files lack sensitive-corpus coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Sensitive-corpus tests do not assert that publish-tail files are included, allowing redaction regressions for new diagnostic tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
