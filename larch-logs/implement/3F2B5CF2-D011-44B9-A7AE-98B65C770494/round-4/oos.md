### FINDING_25: [OUT_OF_SCOPE] Unrelated breadcrumb fixture change
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-awk-extraction-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: The branch includes unrelated `scripts/test-design-log-publish.sh` breadcrumb secret-path/tmpdir fixture changes and run-log artifacts outside the revise-waterfall scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-awk-extraction-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] Other `REVISE_STATUS` consumers may need `ok-fallback`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Other tooling may match only `ok` and misread `ok-fallback` unless repo-wide consumers are audited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] Security docs omit `ok-fallback`, tier-4, and recount behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes snapshot removal only for `REVISE_STATUS=ok` and does not mention `ok-fallback`, tier-4 fallback, or `--recount`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Snapshot copy path may need symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Prior reviews noted possible symlink checks missing for `plan-review/round-N/revise/` sources copied into published artifacts; reviewers marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Rename/copy patch metadata validation is incomplete
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_patch_line` accepts rename/copy metadata that `validate_unified_headers` does not explicitly validate, relying on `git apply` as the backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] Tier-4 fallback may call all external tools
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier-4 fallback can run up to three external tools after unified-diff tiers fail, increasing latency on large plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] Approval gate copy omits `ok-fallback`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Gate B passive-summary text does not mention `ok-fallback`, so operator-facing copy may not reflect tier-4 fallback outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Informational branch and candidate-lifecycle observations
- **Reviewer(s)**: dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt, dyn-harness-equivalence-output.txt
- **Severity**: nit
- **Concern**: Several reviewer notes record branch commits, verified tempdir lifecycle behavior, inner padded extraction ordering, tier-4 non-use of candidate globs, verified harness mappings, and other non-actionable observations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-extraction-output.txt, dyn-candidate-lifecycle-output.txt, dyn-harness-equivalence-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

