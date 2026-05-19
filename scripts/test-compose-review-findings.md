# test-compose-review-findings.sh contract

Regression harness for `scripts/compose-review-findings.sh`.

It verifies empty-input behavior, accepted plan findings, rejected plan
findings, rejected code findings, OOS code findings, JSONL shape with all required keys
(`id`, `issue_number`, `phase`, `outcome`, `reviewer`, `category`,
`round_num`, `prose_body`), per-record field values via `jq`, reviewer
attribution from body metadata, round attribution for code-review artifacts,
secret redaction in the `prose_body` field, literal preservation of `<`, `>`,
and `&` (no HTML escaping under JSONL), category derivation from a leading
`## <cat>: ...` body line, and usage failure envelopes.
