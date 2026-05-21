### FINDING_26: [OUT_OF_SCOPE] test harness `bash [[ ]]` vs shipped `sh`-style operator scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Tests use Bash idioms not identical to the shipped audit operator script surface; may be acceptable test-only convention unless repo-wide strict `bash 3.2` parity is required.
- **Suggested revision**: Accept as test-only convention or refactor tests if strict portability is required repo-wide.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] case-sensitive “Since Last Audit” operator input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Strict casing can surprise operators (e.g. `Since Last Audit` vs expected form).
- **Suggested revision**: Document in SKILL or defer normalized casing to a future change.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] `test-audit-runs.md` contradicts current empty-verbal behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Doc still frames empty verbal description as a usage error while tests/SKILL treat empty as implicit since-last-audit.
- **Suggested revision**: Update the contract bullet in a separate doc-only change.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] tests mirror `audit-resolve-prs` classifiers instead of always shelling out
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Duplicated logic is not mechanically coupled to production parsing.
- **Suggested revision**: Prefer invoking real scripts for dispatch edge cases or share one sourced parser module ( overlaps directionally with FINDING_12 but flagged out-of-scope by source).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] KV vs YAML naming split for changelog counters is intentional
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Uppercase KV names vs snake_case YAML keys is a deliberate split; `parse_prior` targets YAML consistently.
- **Suggested revision**: No change required beyond optional clarifying note if maintainers find it confusing.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] `audit-resolve-prs.sh` emit paths include all six documented keys
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: `emit_error` / `emit_ok` appear consistent with `audit-resolve-prs.md`’s six-key contract.
- **Suggested revision**: None (informational confirmation).


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] `audit-close-priors.sh` matches `audit-close-priors.md` / SKILL narratives
- **Reviewer(s)**: dyn-kv-contract-output.txt
- **Concern**: Per-issue `CLOSE_FAILED`/`REASON` and `ISSUE_LIST_FAILED` shapes align with documented contracts (includes branch commit references in source).
- **Suggested revision**: None (informational confirmation).


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] `last N PRs` verbal parsing robustness (`grep -oE`)
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Digit extraction can behave poorly if multiple digit runs/lines appear; primarily robustness, not a demonstrated injection against `jq`.
- **Suggested revision**: Harden parsing if desired; not prioritized as a security finding by source.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_34: [OUT_OF_SCOPE] `normalize_repo` not applied to `--repo` exotic URL shapes
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Identity-check accuracy edge cases for non-canonical `github.com` placement vs focusing on `remote.origin.url`.
- **Suggested revision**: Optional hardening separate from dotted-segment `.git` bug (FINDING_5).


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] informational closure on scan-run PR-body digit constraints
- **Reviewer(s)**: dyn-shell-injection-output.txt
- **Concern**: Source asserts certain fields/patterns limit injection surface described elsewhere; no additional in-scope security finding beyond listed items.
- **Suggested revision**: None (informational).
```

Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=1 Result=rejected

