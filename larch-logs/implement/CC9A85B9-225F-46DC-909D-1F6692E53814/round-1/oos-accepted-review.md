### FINDING_15: [OUT_OF_SCOPE] Verifier lacks absolute-path rejection for TSV rows vs audit-scan-run
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Pre-existing asymmetry; optional hardening in a follow-up.
- **Suggested revision**: None for this PR unless explicitly widening scope.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_16: [OUT_OF_SCOPE] `load_required_files` synthetic harness omits step8/step9a1
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Pre-existing harness limitation for synthetic complete dirs.
- **Suggested revision**: Widen separately if desired.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_17: [OUT_OF_SCOPE] Verifier uses same unquoted glob expansion style for manifest-fixed paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Risk mainly if `docs/run-logs-required-files.tsv` is maliciously or mistakenly edited; same class as audit glob hardening.
- **Suggested revision**: Apply shared validation/allowlist or treat as follow-up outside this change.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_18: [OUT_OF_SCOPE] `sort -V` portability in `scan_cache_freshness`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Older BSD `sort` may mishandle `-V` or abort; pre-existing semver compare dependency.
- **Suggested revision**: Track separately from this diff.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_19: [OUT_OF_SCOPE] Scout notes: `shopt nullglob` restored after loop including `break`
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that `nullglob` is disabled after `done` even when the loop exits via `break` (not reported as a defect requiring change).
- **Suggested revision**: None unless product owners want explicit documentation.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


