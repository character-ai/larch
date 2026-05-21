### FINDING_18: [OUT_OF_SCOPE] `audit-close-priors.sh` intentionally lacks unit tests (integration-only posture)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Close-priors behavior is manual/`gh`-integration oriented by contract; not necessarily a regression introduced by this diff’s stated test plan, but it concentrates risk in manual runs.
- **Suggested revision**: Keep as documented policy **or** add opt-in hermetic `gh` stub tests if policy changes.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_39: [OUT_OF_SCOPE] Bash 3.2 “advanced construct” checklist: no violations found in new audit-runs scripts/tests
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Reviewer reports no `declare -A`, `mapfile`, `${var^^}`, `&>>`, `coproc`, etc., in the touched audit-runs surface (maintenance/verification note).
- **Suggested revision**: None required beyond keeping future edits within `BASH_AUTHORING.md` constraints.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] `audit-pacific-timestamp.sh` manual fallback labeled behavioral approximation (non-Bash issue)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: TZ-based conversion path plus `%z` normalization is considered reasonable on macOS/BSD; manual fallback is an intentional approximation rather than a Bash construct incompatibility.
- **Suggested revision**: If behavior changes, document approximation limits; no Bash-only action implied here.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] Tooling/version dependencies (`jq`, `gh`, `sort -V`, `git branch`)
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Concern**: Scripts depend on external tool behaviors/flags outside the Bash construct checklist (environment matrix concern).
- **Suggested revision**: Track under installation/docs/CI image policy rather than bash-only linting.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] Legacy inline parser tests duplicate production regexes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Older inline parser tests duplicate production regexes, increasing maintenance burden; not uniquely introduced/resolved by this branch alone.
- **Suggested revision**: Refactor tests to call scripts/shared parsers opportunistically the next time this area is touched (policy-level cleanup).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

