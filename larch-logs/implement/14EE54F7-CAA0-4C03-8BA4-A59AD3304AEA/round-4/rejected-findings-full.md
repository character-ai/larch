### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Fail-open BEHIND_COUNT=0 on fetch/rev-list errors in post-fix push path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ci-behind-count.sh` / ship-pr behind-check fail-open to `BEHIND_COUNT=0` on fetch or `rev-list` errors. Transient git/network/auth failure or upstream outage makes the branch look current; post-fix CI-fix can plain-push on a stale base without rebasing onto latest main/upstream—the churn #3210 targets. Document fail-open, stall/retry when behind cannot be computed, emit unknown state, or make post-fix behind-check failures blocking; keep fail-open only where explicitly required (e.g. ci-status polling).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: first-fixer-non-health may target wrong tier when Claude unavailable first
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: When Claude is skipped as the first tier, `waterfall_iter` shifts before Codex runs; `first-fixer-non-health` may target the wrong tier. Track the first actually-launched tier for `first-fixer-non-health`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: ci-behind-count harness never exercises default fetch path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: All harness cases use `--no-fetch` only; default fetch behavior in `ci-behind-count.sh` is never exercised. Add one fetch-path fixture with a local origin remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: did_rebase set before run_rebase_rebump completes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `did_rebase` is set before `run_rebase_rebump` completes; a future non-fatal rebase return could force-push without a completed rebase. Set `did_rebase` after successful rebase helper return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Duplicate BEHIND_COUNT parsing (awk vs kv_value)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` uses `awk` for `BEHIND_COUNT` while `ship-pr.sh` uses `kv_value`—two parsers for the same contract stream. Unify on `kv_value` or a shared parse helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

