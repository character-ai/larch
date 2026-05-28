## Proposed Design Outline

### Goals
- Add a regression test that combines the nospace pseudo-heading (`###FINDING_1:`) with the empty-merge attestation token and asserts validation rejects it with `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation`.
- Add a regression test that exercises all-OOS input + attestation-only aggregate output and locks in current acceptance (`REASON=ok`, `MERGED_COUNT=0`).

### Non-goals
- Modify `skills/review/scripts/aggregate-findings.sh` behavior, validator branches, or any production code.
- Add new rejection paths for the all-OOS + attestation-only combo (the recommended outcome is to encode current acceptance).
- Refactor or rename existing fixtures or assertion blocks.

### Approach sketch
- Extend the fixture `case` in `write_finding_fixture` with one new kind for gap 1 (nospace pseudo-heading body that also embeds the `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token).
- Add a new top-level assertion block for gap 1 next to existing `zero_findings_nospace_pseudo_heading` / `zero_findings_nonconforming_with_attestation` tests; assert `AGGREGATED=false`, `REASON=validation-failed`, and the specific `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation` token from stderr.
- Add a new top-level assertion block for gap 2 using a new input fixture where every reviewer slot is `[OUT_OF_SCOPE]` and the aggregator stub returns `zero_findings_pure_attest`; assert `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`, and `assert_whitespace_only`.
- Total scope ~30–35 lines (matches OOS issue estimate).

### Surfaces in scope
- `skills/review/scripts/test-aggregate-findings.sh` — fixture case + two new assertion blocks only.

### Open questions
- None.
