# parse-judge-vote-and-rating.sh

Parses one anchored ballot line from a voter file:

```text
parse-judge-vote-and-rating.sh <voter_file> <ballot_id>
```

Both positional arguments are required. A missing argument or unreadable voter
file is a hard non-zero exit.

On success the script emits quiet-mode `KEY=value` lines:

- `PARSED_VOTE=<YES|NO|EXONERATE|>`
- `PARSED_CORRECTNESS=<true|partially-true|false-positive|uncertain|>`
- `PARSED_SEVERITY=<blocker|major|minor|nit|uncertain|>`
- `PARSED_QUALITY=<excellent|good|adequate|weak|no-fix|uncertain|>`
- `PARSED_UNCERTAIN=<true|false>`

No matching `<ID>:` line exits 0 with empty vote and empty axis values. A
matching line whose token after `:` is not `YES`, `NO`, or `EXONERATE` also
exits 0 with an empty vote. Vote tokens are matched case-insensitively and
emitted upper-case.

Axis values are lowercase-only. Non-lowercase or otherwise unrecognized axis
values emit empty for that axis and force `PARSED_UNCERTAIN=true`. The
uncertain output is `false` only when correctness, severity, quality, and an
explicit lowercase `UNCERTAIN=false` all parse successfully. Missing or
unrecognized axes dominate an explicit `UNCERTAIN=false`.

Duplicate anchored ID lines are last-line-wins, matching
`scripts/lib-vote-tally.sh::vote_for_id`. Axis tokens may appear in any order,
but the vote token must remain immediately after `<ID>:`. Axis parsing only
considers text before the ` -- ` rationale delimiter; axis-looking tokens after
that delimiter are rationale text and are ignored.

Implementation contract: the Bash wrapper invokes one `awk` scan. `awk` emits a
single tab-separated line (`vote`, `correctness`, `severity`, `quality`,
`uncertain`); Bash splits that row and emits the quiet-mode KVs. The awk program
does not call shell helpers.

The per-position `vN_tool` TSV semantics are owned by
`skills/design/scripts/tally-plan-review.md`. Regression coverage lives in
`skills/design/scripts/test-findings-classification.sh`.
