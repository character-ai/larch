# Review Round 3

- Mode: `diff`
- 8 accepted, 13 rejected (13 exonerated)

## Accepted Findings

### FINDING_11: External reviewer prompt redaction/escaping is too narrow
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: Plan and feature-description blocks sent to external reviewers are not scrubbed with the repository’s full secret redactor and do not fully neutralize prompt-control markup. Tests mainly assert block presence rather than a negative matrix for secrets and tag injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.


### FINDING_14: Threshold dedupe lets collector failure override substantive output files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-threshold-output.txt
- **Severity**: important
- **Concern**: `--reviewer-output-files` skips bases already present in collector results even when collector status is failed but the on-disk file is substantive, causing threshold and coverage to disagree and potentially fail recovered static peers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-threshold-output.txt: Address the concern above.


### FINDING_15: Dropped static rows can be double-counted in threshold math
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-threshold-output.txt
- **Severity**: important
- **Concern**: Dropped-slot failures are not deduplicated against prior counted bases or duplicate TSV rows, so logical static slot loss can be inflated past the hard-stop threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-threshold-output.txt: Address the concern above.


### FINDING_17: Collector-result pass can double-count duplicate static stems
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: important
- **Concern**: The threshold script’s collector-results pass does not dedupe normalized static basenames before incrementing counts, so duplicate phase/retry records can inflate failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.


### FINDING_21: `cap_hit` is treated as coverage success
- **Reviewer(s)**: dyn-coverage-gate-output.txt
- **Severity**: important
- **Concern**: The coverage gate treats `cap_hit` like `OK`, so an archetype whose peers were skipped by budget caps can be marked covered even though no substantive static lens ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coverage-gate-output.txt: Address the concern above.


### FINDING_22: Reviewer-testing plan injection can weaken narrowed diff modes
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: `reviewer-testing` now receives plan blocks in narrowed diff modes and description mode, with mode-specific constraints emitted after the untrusted plan, allowing hostile plan text to try to widen review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.


### FINDING_7: Coverage gate can credit invalid static output files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-coverage-gate-output.txt
- **Severity**: important
- **Concern**: The per-archetype coverage gate can treat stale, orphaned, or collector-rejected static output files as successful coverage. This can let a round proceed even when the current manifest has no live substantive peer for an archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-coverage-gate-output.txt: Address the concern above.


### FINDING_9: Missing both-vendor happy-path threshold harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not assert that a healthy both-vendor static panel passes `intended-slots=8` and `launched-slots=8` into threshold logic, leaving denominator regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


