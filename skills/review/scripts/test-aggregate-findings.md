# test-aggregate-findings.sh

Regression harness for `skills/review/scripts/aggregate-findings.sh`. See the primary contract in `skills/review/scripts/aggregate-findings.md`.

## Makefile target

`make test-aggregate-findings` runs `bash skills/review/scripts/test-aggregate-findings.sh` through the repository harness timer.

## Coverage

Exercises the aggregator's empty-merge attestation contract across rejection and success paths, including:

- Pure-token and padded-token zero-findings acceptance cases (`zero_findings_pure_attest`, `zero_findings_padded_attest`, etc.) where successful persistence is whitespace-only.
- Empty-merge rejection cases for missing or impure attestation lines (`zero_findings_no_attest`, `zero_findings_impure_attest`, etc.).
- #2939 regression coverage for pure-attestation round-trip success, nonconforming pseudo-heading plus attestation rejection, and narrative plus attestation success with whitespace-only persistence.
- Merge-success-path persistence-strip coverage via the `merge_plus_impure_attest` stub kind, which asserts the `aggregate-findings.sh` `startswith` predicate strips adjacent-suffix attestation lines before the merged ballot is persisted.
- Validator pre-strip behavior via `drop_impure_empty_merge_attestation_lines`.

## Edit-in-sync rule

When changing the aggregator's empty-merge contract (`EMPTY_MERGE_ATTESTATION` token, validator strip ordering, persistence-strip predicate, or attestation-line shapes), update this harness, its sibling `aggregate-findings.md`, `SECURITY.md`, and docs in the same PR.
