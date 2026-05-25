# test-aggregate-findings.sh

Regression harness for `skills/review/scripts/aggregate-findings.sh`. See the primary contract in `skills/review/scripts/aggregate-findings.md`.

## Makefile target

`make test-aggregate-findings` runs `bash skills/review/scripts/test-aggregate-findings.sh` through the repository harness timer.

## Coverage

Exercises the aggregator's empty-merge attestation contract across rejection and success paths, including:

- Pure-token zero-findings acceptance and rejection cases (`zero_findings_padded_attest_rejected`, `zero_findings_impure_attest`, etc.).
- Merge-success-path persistence-strip coverage via the `merge_plus_impure_attest` stub kind, which asserts the `aggregate-findings.sh` `startswith` predicate strips adjacent-suffix attestation lines before the merged ballot is persisted.
- Validator pre-strip behavior via `drop_impure_empty_merge_attestation_lines`.

## Edit-in-sync rule

When changing the aggregator's empty-merge contract (`EMPTY_MERGE_ATTESTATION` token, validator strip ordering, persistence-strip predicate, or attestation-line shapes), update this harness and its sibling `aggregate-findings.md` in the same PR.
