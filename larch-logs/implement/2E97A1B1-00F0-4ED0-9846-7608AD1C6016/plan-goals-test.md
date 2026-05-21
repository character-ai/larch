## Goal
Fix aggregate-findings.sh validator: treat zero FINDING blocks as valid clean pass when attested, normalize slot labels with trailing parentheticals (input and output), and align prompts/docs/tests.

## Implementation Plan

### Objective
Fix the aggregate-findings.sh inline Python validator for failure shapes observed in production (issue #2536), with an explicit empty-merge attestation on the raw vendor output before a zero-`### FINDING_` ballot replace, symmetric slot normalization, and CI coverage for both success and failure paths.

### Files to Modify
- `skills/review/scripts/aggregate-findings.sh` — inline Python validator (`validate_py` heredoc) and post-validation staging (strip attestation before persisting when merge output has zero finding blocks)
- `skills/review/scripts/test-aggregate-findings.sh` — regression harness (success path, negative missing-attestation path)
- `skills/review/scripts/aggregate-findings.md` — shipped contract / operator documentation
- `agents/orchestrator-aggregator.md` — orchestrator prompt (empty-merge attestation instructions must be unambiguous for models)
- `SECURITY.md` — trust-boundary note for aggregation + attestation

### Approach

#### Zero FINDING blocks + attestation
When aggregator output has no `### FINDING_` blocks but the input ballot still does, require a full-line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` in the raw vendor output; otherwise fail closed (`validation-failed`) and leave `findings.md` unchanged. After validation passes, strip that line before atomic replace so the persisted ballot stays human-facing.

#### Labelled slot normalization
Normalize trailing parenthetical suffixes on **both** input and output reviewer slot tokens so membership / dedup checks stay consistent.

#### Regression tests
1. **zero_findings**: Stub emits narrative plus attestation; expect `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`, zero `### FINDING_` lines in updated findings, and **no** persisted attestation line.
2. **zero_findings_no_attest**: Stub emits narrative only; expect `validation-failed` and unchanged input ballot.
3. **labelled_slot**: Stub emits merged finding with parenthetical suffix on a reviewer slot; expect successful merge.

### Testing Strategy
Run `make test-aggregate-findings` to verify all existing tests still pass and new tests pass. Also run `/relevant-checks` (which includes `make lint`).

### Edge Cases
- `normalize_slot` strips only the last parenthetical suffix.
- Empty-merge output that is only the attestation line becomes a newline-only ballot after strip (non-empty file for downstream tooling).

diff_lines: ~80

## Test plan
(no test plan section in plan-file)
