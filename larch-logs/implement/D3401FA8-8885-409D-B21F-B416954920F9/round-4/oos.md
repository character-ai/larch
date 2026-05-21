### FINDING_10: [OUT_OF_SCOPE] Concurrency preflight test compares timestamps as strings not `jq` ISO logic
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Test helper ordering may diverge from production’s `jq`-based ISO comparison; optional alignment with pre-existing test style.
- **Suggested revision**: Optionally align the test comparator with the production `jq` path if parity matters.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: [OUT_OF_SCOPE] Manual America/Los_Angeles timestamp fallback is not faithful LA local time
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When the real `America/Los_Angeles` TZ path fails, the manual fallback mixes UTC calendar parts with coarse DST/month heuristics and incomplete day rollover, so `audit_timestamp` and titles can be wrong near DST boundaries or yield invalid/implausible calendar days; some sources treat this as pre-existing/low trust-boundary impact rather than a new regression.
- **Suggested revision**: Prefer a portable correct TZ implementation, hard-fail to explicit UTC `Z` with a loud warning, or document uncertainty and remove fragile manual arithmetic.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] `audit-close-priors.sh` discards `gh` stderr on failures
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Long-standing pattern makes token/permission failures harder to diagnose from logs alone.
- **Suggested revision**: Optionally surface `gh` stderr on failure.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] `rej-category-blank` missing from SKILL scan table while present in `scans.tsv`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Pre-existing doc/registry skew; should be fixed when the table is next edited.
- **Suggested revision**: Add the missing row alongside other table edits.
```

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] `sed`-based remote URL normalization edge cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Uncommon remote URL shapes may normalize incorrectly; treated as a long-standing pattern worth revisiting only if real clones hit it.
- **Suggested revision**: Revisit normalization only with evidence of bad URLs; otherwise leave as known limitation.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

