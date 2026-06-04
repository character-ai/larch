### FINDING_12: [OUT_OF_SCOPE] Unrelated merge parity target broadens PR scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-merge-parity` appears bundled with report-tokens work, increasing PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] Workflow resolution is duplicated between Bash and Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bash and Python workflow resolution can diverge on SIMPLE/HARD classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Bail and stalled exits share code 4
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `EXIT_BAIL` and `EXIT_STALLED` share an exit code, so callers cannot distinguish them by status alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Wrapper-level issue posting failure coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cli-bridge-output.txt
- **Severity**: nit
- **Concern**: The quiet wrapper harness does not exercise `gh issue create` or issue-body trim hard failures under quiet-mode env vars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-cli-bridge-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] SECURITY.md names stale redaction implementation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` references stale `redact-secrets.sh` wording instead of the current Python redaction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] Mixed per-vendor bucket/blended pricing is intentional
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: Mixed per-vendor bucket versus blended argv can change totals versus historical reports, but was identified as an intentional plan change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] Plot and table date-axis mismatch is accepted legacy behavior
- **Reviewer(s)**: dyn-token-pricing-output.txt, dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Plots use `closed_at` while per-day tables use `started_at`; reviewers marked this as documented/preserved behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt, dyn-log-scan-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] Design `unknown` workflow runs are omitted from SIMPLE/HARD trend and plot grouping
- **Reviewer(s)**: dyn-token-pricing-output.txt, dyn-log-scan-output.txt
- **Severity**: latent
- **Concern**: Design runs with `workflow="unknown"` are included in aggregate/headline surfaces but excluded from SIMPLE/HARD trend and plot series; one source marked this out-of-scope for pricing math.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt, dyn-log-scan-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_42: [OUT_OF_SCOPE] Quiet wrapper restores stderr as an improvement
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: nit
- **Concern**: Restoring both stdout and stderr before Python exec is noted as an improvement over the removed bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] Limit counts scanned directories rather than parsed records
- **Reviewer(s)**: dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Low `LARCH_REPORT_TOKENS_LIMIT` values can yield zero parseable runs because the limit counts scanned directories, which was called out as a known quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-scan-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_44: [OUT_OF_SCOPE] Scan fail-soft behavior matches stated contracts
- **Reviewer(s)**: dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Bad JSON, missing numeric totals, bucket gaps, repo-slug fail-soft behavior, and implement unknown workflow inclusion were identified as matching contracts except for separately noted design reconciliation concerns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-scan-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_50: [OUT_OF_SCOPE] Report-tokens live behavior aligns with plan
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: nit
- **Concern**: The reviewer marked current report-tokens wrapper/CLI/issue behavior as aligned with the #3434 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_51: [OUT_OF_SCOPE] Bash remains the default ship-pr runtime
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: nit
- **Concern**: Python merge/run-context/finalize gaps matter when the Python driver is selected or modules are exercised directly; default runtime remains bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_52: [OUT_OF_SCOPE] Parity harness lacks Python-vs-bash version-race pairing
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: latent
- **Concern**: Existing merge parity coverage does not pair Python and bash behavior for version-race or bump-subject scenarios still enforced by `merge-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

