### FINDING_1: Duplicate initial BEHIND fast-path blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate BEHIND handling exists before and after initial UNKNOWN retry, creating drift risk if one branch is edited independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Initial UNKNOWN retry comment is stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Comment still describes immediate error short-circuit rather than retry-then-fail behavior, which could mislead maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: G4 empty ERROR assertion should be more explicit
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: G4’s ERROR assertion is reported as less explicit than adjacent tests, making accidental non-empty ERROR regressions harder to catch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Post-force-push UNKNOWN-to-BEHIND recovery lacks BEHIND re-route
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Post-force-push UNKNOWN retry can resolve to BEHIND without taking the empty-ERROR BEHIND fast path, yielding misleading or inconsistent routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Retry counts are hard-coded
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Retry counts 4 and 3 are hard-coded at call sites, increasing readability drift as more call sites appear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Missing transient empty-to-CLEAN recovery test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Harness coverage lacks a transient empty merge-state resolving to CLEAN case, so empty-string recovery could regress while UNKNOWN-to-CLEAN still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Post-force-push error text may mislabel empty state as UNKNOWN
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Post-force-push error text says UNKNOWN even when the state may be empty, producing misleading operator output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Initial UNKNOWN exhaustion adds real wall time
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Persistent initial UNKNOWN or empty merge state now waits up to about 20 seconds before returning MERGE_RESULT=error; harness stubs sleep, so timing impact is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: E1 lacks empty ERROR assertion for first-shot BEHIND
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: First-shot BEHIND coverage does not assert empty ERROR, so a regression emitting a non-empty ERROR could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] No live GitHub timing integration test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Real GitHub propagation delay behavior is only validated manually, leaving live timing behavior outside automated coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] PR and repo arguments lack validation beyond non-empty
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--pr` and `--repo` values are only checked for non-empty before flowing as quoted `gh` argv values; this is pre-existing and not shell-string interpolation, but remains an input-validation gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] API-sourced MERGE_STATE can affect stdout key parsing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: API-sourced MERGE_STATE is embedded in ERROR strings; newline-containing values could confuse naive key=value stdout parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Flush-recovery docs imply BEHIND routing that does not exist
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Flush-recovery prose says BEHIND after post-force-push UNKNOWN retry uses existing post-recovery routing, but that is only true for first-shot BEHIND before the retry loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
