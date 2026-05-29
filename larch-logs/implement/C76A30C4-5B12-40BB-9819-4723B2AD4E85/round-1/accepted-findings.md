### FINDING_11: no tests for lib-quiet redaction warning paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-quiet.sh` does not cover redactor-unavailable or redactor-failed warning branches, so regressions in those fallback paths could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: breadcrumb-monitor truncated flag parsing can exit non-zero
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/breadcrumb-monitor.sh` uses `shift 2` under `set -e`, so malformed paired flags such as a lone `--stream` can make the shim exit non-zero despite the intended always-exit-0 contract, affecting fence routing and potentially masking writer results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: no minimal regression test for breadcrumb-monitor shim
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Monitor and lint harnesses were deleted without a small replacement test proving the Stage 3 no-op shim exits 0 for representative arguments and avoids reintroducing removed dependencies, so regressions can pass lint and fail production fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: stale relevant-checks comment references removed linter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` still contains a stale `lint-foreground-markers` comment after that linter was removed, misleading contributors who search for the removed check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


