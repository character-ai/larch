### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Awk suffix / character-class test for flags may be non-portable across awk implementations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: An awk test using `/[A-Za-z0-9_-]/`-style boundary logic can behave differently across awk implementations and help punctuation, causing false unknown-flag or false OK results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite boundary test without ambiguous bracket ranges


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `SKIPPED_COUNT` summary excludes `SKIPPED_FLAG_CHECK`, misleading KV totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Summary KVs undercount skips when `SKIPPED_FLAG_CHECK` is omitted from `SKIPPED_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Count SKIPPED_FLAG_CHECK or rename KV field


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

