### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: Fixture correctly combines `###FINDING_1:` (no space after `###`) with `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, mirroring the spaced `zero_findings_nonconforming_with_attestation` sibling.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Fixture correctly combines `###FINDING_1:` (no space after `###`) with `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, mirroring the spaced `zero_findings_nonconforming_with_attestation` sibling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: Assertions match the narrow-trigger contract in `aggregate-findings.sh`: `REASON=validation-exhausted` (not `validation-failed`), `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation`, and `cmp -s` on rejection — aligned with the `has_nonconforming_finding_heading_markers(outtext) and has_attest_line` branch at lines 555–559.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Assertions match the narrow-trigger contract in `aggregate-findings.sh`: `REASON=validation-exhausted` (not `validation-failed`), `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation`, and `cmp -s` on rejection — aligned with the `has_nonconforming_finding_heading_markers(outtext) and has_attest_line` branch at lines 555–559.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Placed immediately after the nospace-without-attestation block (`validation-failed`), which correctly exercises the distinct missing-attestation path when the token is absent.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Placed immediately after the nospace-without-attestation block (`validation-failed`), which correctly exercises the distinct missing-attestation path when the token is absent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: `aggregator-validate.stderr` is overwritten each run via `2>"$REVIEW_TMPDIR/aggregator-validate.stderr"` (line 643), so ordering side effects are not a concern.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `aggregator-validate.stderr` is overwritten each run via `2>"$REVIEW_TMPDIR/aggregator-validate.stderr"` (line 643), so ordering side effects are not a concern. **Gap 2 — all-OOS input + `zero_findings_pure_attest`**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: Assertions lock the intended contract: success (`AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`), no `AGGREGATOR_VALIDATION_FAILED=` token, and `assert_whitespace_only` on the work file after acceptance — consistent with `zero_findings_round_trip_pure_attestation_success` (#2939).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Assertions lock the intended contract: success (`AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`), no `AGGREGATOR_VALIDATION_FAILED=` token, and `assert_whitespace_only` on the work file after acceptance — consistent with `zero_findings_round_trip_pure_attestation_success` (#2939).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Placement after `oos_shared_slot_merge` (#2491) is appropriate: it documents the opposite case (enforcement when `blocks` is non-empty vs. skipped when empty).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Placement after `oos_shared_slot_merge` (#2491) is appropriate: it documents the opposite case (enforcement when `blocks` is non-empty vs. skipped when empty).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: The test’s stated goal is to catch a **refactor that applies `oos_only_slots` enforcement on the empty-merge path**; it is not designed to prove `oos_only_slots` is non-empty if OOS tagging regresses but empty-merge still accepts — that limitation is explicit in the plan and is acceptable for this regression scope.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - The test’s stated goal is to catch a **refactor that applies `oos_only_slots` enforcement on the empty-merge path**; it is not designed to prove `oos_only_slots` is non-empty if OOS tagging regresses but empty-merge still accepts — that limitation is explicit in the plan and is acceptable for this regression scope. **Acceptance criteria:** Fixture arm, both assertion blocks, issue tags `(#3003)`, and no production changes all match the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: Gap 1: `_PSEUDO_FINDING_HEADING` (`^###\s*FINDING_[0-9]`) matches `###FINDING_1:`; with attestation, validator branch at `aggregate-findings.sh:555–560` emits `nonconforming_heading_with_attestation` → pipeline `MERGE_PIPELINE_RC=1` → `REASON=validation-exhausted` (lines 772–784). Assertions match the sibling `zero_findings_nonconforming_with_attestation` block (lines 915–930).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 1: `_PSEUDO_FINDING_HEADING` (`^###\s*FINDING_[0-9]`) matches `###FINDING_1:`; with attestation, validator branch at `aggregate-findings.sh:555–560` emits `nonconforming_heading_with_attestation` → pipeline `MERGE_PIPELINE_RC=1` → `REASON=validation-exhausted` (lines 772–784). Assertions match the sibling `zero_findings_nonconforming_with_attestation` block (lines 915–930).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Gap 1 without attestation still correctly expects `validation-failed` (missing-attestation path, RC=2) in the preceding nospace-only test (lines 952–965).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 1 without attestation still correctly expects `validation-failed` (missing-attestation path, RC=2) in the preceding nospace-only test (lines 952–965).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: Gap 2: All-OOS input builds non-empty `oos_only_slots`; attestation-only output has `blocks == []`, so the `oos_only_slots` loop at lines 602–610 never runs — `REASON=ok` is the intended locked behavior per the plan.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 2: All-OOS input builds non-empty `oos_only_slots`; attestation-only output has `blocks == []`, so the `oos_only_slots` loop at lines 602–610 never runs — `REASON=ok` is the intended locked behavior per the plan. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `05e54b6c` — Add missing attestation-only empty-merge regression tests (#3003)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `05e54b6c` — Add missing attestation-only empty-merge regression tests (#3003)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: `d36b0033` — chore(larch-logs): flush implement run (per policy, not reviewed as product risk)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `d36b0033` — chore(larch-logs): flush implement run (per policy, not reviewed as product risk) **Scope:** Only `skills/review/scripts/test-aggregate-findings.sh` changes product behavior (tests only); `aggregate-findings.sh` is unchanged, matching the plan. ### Edge-case / failure-recovery assessment **Gap 1 — `zero_findings_nospace_pseudo_heading_with_attestation`**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

