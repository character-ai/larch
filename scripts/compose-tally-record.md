# compose-tally-record.sh contract

`scripts/compose-tally-record.sh` wraps a file-backed plan-review or
code-review tally body in the canonical JSON object used by
`plan-review-tally.json` and `code-review-tally.json`.

Inputs:

```text
--phase plan-review|code-review
--mode simple|hard
[--rounds N]
[--accepted N]
[--rejected N]
--body-file PATH
```

The output is a single JSON object on stdout with `schema_version`, `phase`,
`batch`, `mode`, `rounds`, `accepted_count`, `rejected_count`, and `body`.
The `plan-review` phase maps to `batch: "plan-review-tally"`; the
`code-review` phase maps to `batch: "code-review-tally"`. The body file is
embedded verbatim as a JSON string by `jq --rawfile`.

The helper rejects missing body files, symlinks, invalid phase or mode values,
and non-numeric tally counts. It does not redact content; `larch-log.sh` still
applies the standard tmpdir and secret redaction pass before writing.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
