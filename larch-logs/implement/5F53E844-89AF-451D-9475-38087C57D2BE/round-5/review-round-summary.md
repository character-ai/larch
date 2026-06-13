# Review Round 5

- Mode: `diff`
- 3 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_5: Deleted `test-findings-classification.sh` forensic fixtures not ported to pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-findings-classification.sh` forensic fixtures are not ported to pytest. `make test-review-findings-classification` still runs in CI shard 14 but no longer guards nested vs standalone TSV paths, `JUDGE_ERROR` rows, enum sanitization, or log-phase round publishes; committed run-log TSV can drift undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port fixtures A–H from the deleted shell harness into pytest with CSV/header assertions and log-batch write checks.


### FINDING_6: Plan-required `body_severity` and `focus_area` extraction tests missing from pytest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required `body_severity` and `focus_area` extraction tests are missing. Deleted `test-compose-review-findings.sh` `FINDING_TRUNC` fixture ensured analyzers keep severity/focus after `prose_body` truncation; regressions would ship green in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest asserting body_severity, focus_area, and truncated prose_body on a long-body fixture matching the old harness.


### FINDING_7: Description-mode `gather-context` regression coverage dropped
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Description-mode gather-context regression coverage was dropped. Deleted `test-gather-context.sh` verified `MODE=description`, scope resolution, and stdout cap; description-mode review can break while diff-mode tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add description-mode gather-context pytest with fixture git repo and scope/KV assertions.


