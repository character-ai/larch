# Review Round 2

- Mode: `diff`
- 3 accepted, 6 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Bash 3.2 incompatibility breaks `--zones`
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The zone-resolution fence uses Bash 4-only `mapfile`, but default macOS Bash 3.2 does not provide it, so `--zones` fails before preparation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Replace mapfile with a Bash 3.2-safe read loop plus unique non-empty RESOLVED_SEARCH check
  - From codex-specialist-correctness: Replace mapfile with a Bash 3.2-compatible while IFS= read -r parser that counts and stores RESOLVED_SEARCH records before applying the existing validation.
  - From cursor-specialist-edge-cases: Use Bash 3.2-safe parsing (sed plus single-match count) or keep uniqueness enforcement entirely in Python.
  - From codex-specialist-edge-cases: Use Bash-3.2-compatible line parsing while preserving the unique non-empty result check.
  - From codex-specialist-testing: Use a Bash 3.2-compatible scalar or read-loop parser that enforces one non-empty RESOLVED_SEARCH record, and add a structural portability assertion rejecting mapfile/readarray.


### FINDING_11: Validate-report failure does not halt orchestration
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The validate-report fence does not check the CLI exit status, so later marker-writing or filing steps may proceed after contract validation fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Wrap validate-report in if ! ...; then exit 2; fi and optionally require REPORT_CONTRACT=pass on stdout.


### FINDING_12: Structural harness asserts a stale `RESOLVED_SEARCH` implementation
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Structural test B.6 searches for an obsolete `RESOLVED_SEARCH=$(printf` form that the changed skill no longer contains, causing required verification to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Update the assertion for the validated parser or restore a compatible assignment form.
  - From cursor-specialist-testing: Update (B.6) to pin mapfile parsing, unique non-empty RESOLVED_SEARCH, and exit 2 on resolver failure.
