### FINDING_1: [OUT_OF_SCOPE] run-analysis.sh loses dedicated regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Deleting `test-rate-assertions.sh` and `test-report-tokens-recompute.sh` removes the only `make lint`/offline harness coverage that invoked `skills/report-tokens/scripts/run-analysis.sh`. Future regressions in default rate alignment, cost/reporting math, reported-vs-estimated output, `--plot-from` validation, design `-final` discovery, scan/redaction, or GitHub issue body posting could merge with green lint and surface only during manual or production `/report-tokens` runs. Several reviewers note this is accepted by the #3121 plan/no-test policy, but it remains a coverage tradeoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] aggregate-findings #3003 cases look consistent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Branch `6d4dda973` adds `#3003` cases to `test-aggregate-findings.sh`; the stub merge kinds and assertions appear to match `aggregate-findings.sh` narrow-trigger behavior on static review, but this is outside #3121 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] larch-logs additions not reviewed for functional correctness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Large `larch-logs/**` additions on the branch appear to be implement/design run flushes per project convention and were not reviewed for functional correctness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] ACTUAL_SPEND reconciliation may be posted publicly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ACTUAL_SPEND` reconciliation can be included in public GitHub issue bodies if an operator sets `LARCH_REPORT_TOKENS_ACTUAL_SPEND` and omits `--no-issue`, potentially publishing billing deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] stale fixed-name fixture dirs could affect future scans
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If deleted harnesses were previously killed before their `EXIT` trap, stale fixed-name fixture directories under `larch-logs/implement/` or `larch-logs/design/` could remain. Because `run-analysis.sh` scans all larch log runs, those stale fixture trees could inject phantom issue rows until manually removed. The reviewer notes this is not introduced by the removal commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
