### FINDING_1: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **code-quality** `skills/review/scripts/test-aggregate-findings.sh:915-950` — `zero_findings_nonconforming_with_attestation` includes an exec-isolation block that asserts `execution-issues.md` logging, while the new nospace+attestation sibling (967–982) stops at the primary `TMP`-scoped assertions. **Suggested fix:** If you want symmetric guard depth later, add a parallel exec-isolation block for nospace+attestation; the current plan intentionally scoped only the primary assertions, so this is optional follow-up, not a defect in this branch.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **code-quality** `skills/review/scripts/test-aggregate-findings.sh` (harness-wide) — Several tests (including the new all-OOS success case at 809) use `grep -Fq 'AGGREGATOR_VALIDATION_FAILED=' "$TMP/aggregator-validate.stderr" && fail` without clearing stderr first, relying on each `$AGG` invocation to overwrite via `2>`. **Suggested fix:** Pre-existing pattern shared with line 846; only worth hardening if stderr ever stops being truncated per run.
- **Suggested revision**: Address the concern above.

### FINDING_3: Gap 1: `_PSEUDO_FINDING_HEADING` (`^###\s*FINDING_[0-9]`) matches `###FINDING_1:`; with attestation, validator branch at `aggregate-findings.sh:555–560` emits `nonconforming_heading_with_attestation` → pipeline `MERGE_PIPELINE_RC=1` → `REASON=validation-exhausted` (lines 772–784). Assertions match the sibling `zero_findings_nonconforming_with_attestation` block (lines 915–930).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 1: `_PSEUDO_FINDING_HEADING` (`^###\s*FINDING_[0-9]`) matches `###FINDING_1:`; with attestation, validator branch at `aggregate-findings.sh:555–560` emits `nonconforming_heading_with_attestation` → pipeline `MERGE_PIPELINE_RC=1` → `REASON=validation-exhausted` (lines 772–784). Assertions match the sibling `zero_findings_nonconforming_with_attestation` block (lines 915–930).
- **Suggested revision**: Address the concern above.

### FINDING_4: Gap 1 without attestation still correctly expects `validation-failed` (missing-attestation path, RC=2) in the preceding nospace-only test (lines 952–965).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 1 without attestation still correctly expects `validation-failed` (missing-attestation path, RC=2) in the preceding nospace-only test (lines 952–965).
- **Suggested revision**: Address the concern above.

### FINDING_5: Gap 2: All-OOS input builds non-empty `oos_only_slots`; attestation-only output has `blocks == []`, so the `oos_only_slots` loop at lines 602–610 never runs — `REASON=ok` is the intended locked behavior per the plan.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Gap 2: All-OOS input builds non-empty `oos_only_slots`; attestation-only output has `blocks == []`, so the `oos_only_slots` loop at lines 602–610 never runs — `REASON=ok` is the intended locked behavior per the plan. ---
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/review/scripts/test-aggregate-findings.sh:777-810` — The all-OOS test title claims `oos_only_slots` enforcement does not fire, but it never asserts that `oos_only_slots` is non-empty (e.g., via stderr diagnostics or a dedicated helper). If `oos_attributed_slots()` regressed to return `{}` while attestation-only acceptance still succeeded, this test would still pass and would not catch the interaction the plan describes. **Suggested fix:** Optional hardening: grep validator stderr for an attestation-accepted diagnostic that references input FINDING count, or add a narrow unit assertion on slot sets if the harness gains that hook later.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **code-quality** `skills/review/scripts/test-aggregate-findings.sh:929-981` — Gap-1 positive stderr greps (and the existing #2939 pattern at line 929) rely on `aggregator-validate.stderr` being overwritten per validation run (`aggregate-findings.sh:643`), not accumulated; this is pre-existing and works, but a future append-mode change would make these greps flaky. Not introduced by this branch’s logic.
- **Suggested revision**: Address the concern above.

### FINDING_8: `05e54b6c` — Add missing attestation-only empty-merge regression tests (#3003)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `05e54b6c` — Add missing attestation-only empty-merge regression tests (#3003)
- **Suggested revision**: Address the concern above.

### FINDING_9: `d36b0033` — chore(larch-logs): flush implement run (per policy, not reviewed as product risk)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `d36b0033` — chore(larch-logs): flush implement run (per policy, not reviewed as product risk) **Scope:** Only `skills/review/scripts/test-aggregate-findings.sh` changes product behavior (tests only); `aggregate-findings.sh` is unchanged, matching the plan. ### Edge-case / failure-recovery assessment **Gap 1 — `zero_findings_nospace_pseudo_heading_with_attestation`**
- **Suggested revision**: Address the concern above.

### FINDING_10: Fixture correctly combines `###FINDING_1:` (no space after `###`) with `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, mirroring the spaced `zero_findings_nonconforming_with_attestation` sibling.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Fixture correctly combines `###FINDING_1:` (no space after `###`) with `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, mirroring the spaced `zero_findings_nonconforming_with_attestation` sibling.
- **Suggested revision**: Address the concern above.

### FINDING_11: Assertions match the narrow-trigger contract in `aggregate-findings.sh`: `REASON=validation-exhausted` (not `validation-failed`), `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation`, and `cmp -s` on rejection — aligned with the `has_nonconforming_finding_heading_markers(outtext) and has_attest_line` branch at lines 555–559.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Assertions match the narrow-trigger contract in `aggregate-findings.sh`: `REASON=validation-exhausted` (not `validation-failed`), `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation`, and `cmp -s` on rejection — aligned with the `has_nonconforming_finding_heading_markers(outtext) and has_attest_line` branch at lines 555–559.
- **Suggested revision**: Address the concern above.

### FINDING_12: Placed immediately after the nospace-without-attestation block (`validation-failed`), which correctly exercises the distinct missing-attestation path when the token is absent.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Placed immediately after the nospace-without-attestation block (`validation-failed`), which correctly exercises the distinct missing-attestation path when the token is absent.
- **Suggested revision**: Address the concern above.

### FINDING_13: `aggregator-validate.stderr` is overwritten each run via `2>"$REVIEW_TMPDIR/aggregator-validate.stderr"` (line 643), so ordering side effects are not a concern.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `aggregator-validate.stderr` is overwritten each run via `2>"$REVIEW_TMPDIR/aggregator-validate.stderr"` (line 643), so ordering side effects are not a concern. **Gap 2 — all-OOS input + `zero_findings_pure_attest`**
- **Suggested revision**: Address the concern above.

### FINDING_14: Inline fixture uses strict `### FINDING_N:` headings with `[OUT_OF_SCOPE]` and one reviewer per slot (`cursor-a/b/c-output.txt`), so `oos_attributed_slots` and `oos_only_slots` are populated while `blocks` stays empty on the attestation-only stub output.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Inline fixture uses strict `### FINDING_N:` headings with `[OUT_OF_SCOPE]` and one reviewer per slot (`cursor-a/b/c-output.txt`), so `oos_attributed_slots` and `oos_only_slots` are populated while `blocks` stays empty on the attestation-only stub output.
- **Suggested revision**: Address the concern above.

### FINDING_15: Assertions lock the intended contract: success (`AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`), no `AGGREGATOR_VALIDATION_FAILED=` token, and `assert_whitespace_only` on the work file after acceptance — consistent with `zero_findings_round_trip_pure_attestation_success` (#2939).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Assertions lock the intended contract: success (`AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`), no `AGGREGATOR_VALIDATION_FAILED=` token, and `assert_whitespace_only` on the work file after acceptance — consistent with `zero_findings_round_trip_pure_attestation_success` (#2939).
- **Suggested revision**: Address the concern above.

### FINDING_16: Placement after `oos_shared_slot_merge` (#2491) is appropriate: it documents the opposite case (enforcement when `blocks` is non-empty vs. skipped when empty).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Placement after `oos_shared_slot_merge` (#2491) is appropriate: it documents the opposite case (enforcement when `blocks` is non-empty vs. skipped when empty).
- **Suggested revision**: Address the concern above.

### FINDING_17: The test’s stated goal is to catch a **refactor that applies `oos_only_slots` enforcement on the empty-merge path**; it is not designed to prove `oos_only_slots` is non-empty if OOS tagging regresses but empty-merge still accepts — that limitation is explicit in the plan and is acceptable for this regression scope.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - The test’s stated goal is to catch a **refactor that applies `oos_only_slots` enforcement on the empty-merge path**; it is not designed to prove `oos_only_slots` is non-empty if OOS tagging regresses but empty-merge still accepts — that limitation is explicit in the plan and is acceptable for this regression scope. **Acceptance criteria:** Fixture arm, both assertion blocks, issue tags `(#3003)`, and no production changes all match the plan.
- **Suggested revision**: Address the concern above.

