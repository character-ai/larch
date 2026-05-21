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

### FINDING_20: [OUT_OF_SCOPE] Scout notes: `set -e` and `grep` in `|| continue` predicate context
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that bash suppresses `-e` for failures in the RHS of `cmd1 || cmd2` when `cmd1` is a function—behavioral note, not a requested fix.
- **Suggested revision**: None unless tightening error propagation is desired.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Scout notes: nested functions and `_rf_mstat` / `_rf_mpr` initialization
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Observation that nested helpers are valid bash and `jq` failures are tolerated with empty strings consistent with step9a1 usage.
- **Suggested revision**: None.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Triplicated `exn-agg-*` heuristics across TSV and two scripts
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Concern**: Operational drift risk from partial wording updates; framed as broader maintenance risk rather than a single new logic bug.
- **Suggested revision**: Address via consolidation finding (FINDING_2) in a future scoped change.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Committed `larch-logs/implement/...` tree in branch diff
- **Reviewer(s)**: dyn-shell-state-output.txt, dyn-condition-sync-output.txt
- **Concern**: Large partial run-log tree may be intentional for the implementing run but is orthogonal to functional script review unless explicitly part of the product change.
- **Suggested revision**: Confirm intent with authors; trim or relocate if accidental.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] Tests 52–53 do not encode the `exn-agg` grep predicates
- **Reviewer(s)**: dyn-condition-sync-output.txt
- **Concern**: Clarifying observation: only audit and verify encode those substrings; tests cover the “See … committed run log” path only—no third independent implementation to compare for substring drift in the harness.
- **Suggested revision**: None by itself; overlaps motivation for FINDING_2 / FINDING_6 / FINDING_8 when in scope.
```

Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

