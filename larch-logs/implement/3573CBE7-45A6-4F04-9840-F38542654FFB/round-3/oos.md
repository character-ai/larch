### FINDING_20: [OUT_OF_SCOPE] unused preflight --skill parameter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `audit-preflight.sh` validates `--skill` but does not use it beyond enum checking; behavior matches the shared-lock plan but the API may confuse readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] committed run logs may contain session-derived content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Committed implement run logs may contain session-derived content, but this is intentional per `docs/run-logs.md` and not introduced by the `--skill` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] shared audit concurrency guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The audit preflight concurrency guard remains label-wide across skills, so design and implement audits block each other unless `--allow-concurrent` is used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] design registry is intentionally incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scans-design.tsv` currently contains only cache-freshness, so design audits under-report other categories until follow-up adapters land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] rate assertions design fixture residual risk
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: `test-rate-assertions.sh` also uses an in-tree design fixture but includes it in the `EXIT` trap, leaving only residual abnormal-termination cleanup risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_25: [OUT_OF_SCOPE] implement fixture predates branch
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: The implement fixture in `test-report-tokens-recompute.sh` predates this branch and is already covered by cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] report-token harnesses use in-tree fixtures
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: Report-token harnesses intentionally write fixtures under `$REPO/larch-logs/{implement,design}`, unlike audit harnesses that use `${TMPDIR}`, increasing cross-talk risk when cleanup is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] implement map path parity observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Implement `audit-map-runs.sh` default and explicit `larch-logs/implement` paths remain consistent with the implement branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] implement report-token parity observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Implement `run-analysis.sh` still reads implement token/timing reports and validates legacy or new implement analysis report titles for `--plot-from`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] audit-scan-run root guard observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: The new guard rejecting a skill log root as `--run-dir` is additive safety rather than an implement parity regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] audit-close-priors skill scoping observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Skill-scoped title matching in `audit-close-priors.sh` is an intentional multi-skill behavior change rather than an implement-path regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

