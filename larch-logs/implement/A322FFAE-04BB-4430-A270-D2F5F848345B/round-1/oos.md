### FINDING_17: [OUT_OF_SCOPE] TSV-only edits do not route to readability preamble harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: TSV-only edits may skip `test-lint-readability-preamble` when pre-commit is bypassed, leaving manifest-related regressions to later checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Single-quoted pin scanning misses escaped single quotes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Single-quoted literals still use a naive index scan, so escaped single quotes in pins are not verified correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_6: [OUT_OF_SCOPE] BASH_COMPAT smoke is not real Bash 3.2 coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The Bash compatibility harness uses host Bash compat mode rather than a real Bash 3.2 interpreter, and some checks only compare exit status. Runtime-only or parser-output regressions could pass this smoke while still failing stronger Bash 3.2 coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] Design edits route through multiple costly direct targets
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Design edits trigger three direct make targets, adding local latency through foreground, structure, and pin harness checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] test-design-structure.sh edits do not route to its harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Edits to `scripts/test-design-structure.sh` do not trigger `make test-design-structure`, so structural regressions in that harness can slip past relevant-checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Step marker lines with same-line directives are ignored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step-placement awk skips immediately after matching a step marker, so a readability directive on the same physical line as the marker is not counted toward that step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

