### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/test-trailer-awk.sh:37-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_eq_lines exits directly instead of using shared fail() helper Inconsistent failure formatting vs test-gate-b-dedup-plan.sh and test-trailer-helpers.sh makes triage slightly harder when mixing harness output Delegate assertion failures to fail() after formatting got/want
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: `test-trailer-awk.sh` covers all four awk modes and the normative edge cases from the plan: `block_len` vs distinct keys (duplicate `diff_added:`), last-match-wins, `08`/`09` rejection vs `010` retention, `mechanical_churn` true/false, block boundary, blank-line boundary, and no-trailers.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `test-trailer-awk.sh` covers all four awk modes and the normative edge cases from the plan: `block_len` vs distinct keys (duplicate `diff_added:`), last-match-wins, `08`/`09` rejection vs `010` retention, `mechanical_churn` true/false, block boundary, blank-line boundary, and no-trailers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: Expected `has_key` exit **1** probes use `set +e` / `set -e` with explicit `rc` checks; the round-4 split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1) matches awk semantics and is documented in `test-trailer-awk.md`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Expected `has_key` exit **1** probes use `set +e` / `set -e` with explicit `rc` checks; the round-4 split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1) matches awk semantics and is documented in `test-trailer-awk.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: `(3175)` pins replace weak `snapshot` substrings with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` (BSD-safe); preservation greps at 404–405, 409–410, 412–415 are untouched.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `(3175)` pins replace weak `snapshot` substrings with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` (BSD-safe); preservation greps at 404–405, 409–410, 412–415 are untouched.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Harness is `100755` and invoked from `test-trailer-helpers.sh` (existing `make test-trailer-helpers` / shard-12 path; no orphan shard target needed).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Harness is `100755` and invoked from `test-trailer-helpers.sh` (existing `make test-trailer-helpers` / shard-12 path; no orphan shard target needed).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/test-trailer-awk.sh:18-21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead shift in write_fixture after taking name Misleading API shape for future editors who might expect additional positional fixture args Remove the unused shift
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/test-trailer-awk.sh:14-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] trailer_nr() duplicates _plan_optional_trailer_nr() without sync comment If last-non-empty-line semantics change in lib-plan-optional-trailers.sh only, awk unit tests and production wrappers diverge silently Add must-stay-in-sync comment or extract shared one-liner
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: risk-integration: skills/design/scripts/test-trailer-awk.sh:76-219
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No diff_deleted-only fixture; diff_deleted always paired with diff_added in tests. A regression that only breaks diff_deleted parsing when diff_added is absent could pass keys/values/has_key on combined fixtures while check-plan-size or preservation logic fails on deletion-only plans. Add a diff_deleted-only fixture and assert parse/keys/values/has_key per plan edge-case intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: risk-integration: skills/design/scripts/test-trailer-awk.md:13-17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract omits blank-before-diff-lines case documented in plan block-boundary edge case. Future editors may remove the blank-line fixture thinking it is redundant with boundary-orphan-only. Mention blank-before-diff-lines in the block-boundary section of test-trailer-awk.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

