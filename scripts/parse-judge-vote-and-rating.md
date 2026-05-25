# parse-judge-vote-and-rating.sh

`scripts/parse-judge-vote-and-rating.sh <voter_file> <ballot_id>` parses the last anchored vote line for one ballot id.

Stdout is quiet-stream `KEY=value` lines: `PARSED_VOTE`, `PARSED_CORRECTNESS`, `PARSED_SEVERITY`, `PARSED_QUALITY`, and `PARSED_UNCERTAIN`.

Exit behavior:

- Missing args or unreadable voter file: non-zero.
- No matching `<ID>:` line: exit 0 with empty vote/axis values and `PARSED_UNCERTAIN=true`.
- Matching line with `YES`, `NO`, or `EXONERATE` immediately after `:`: exit 0 with the vote uppercased.
- Matching line with any other immediate token: exit 0 with `PARSED_VOTE=` so callers treat it like `JUDGE_ERROR`.

Axis tokens may appear in any order on the same line: `CORRECTNESS=`, `SEVERITY=`, `QUALITY=`, `UNCERTAIN=`. Axis values are lowercase-only. Non-lowercase or unknown values are unrecognized and emit empty for that axis. Vote tokens remain case-insensitive for compatibility with `scripts/lib-vote-tally.sh::vote_for_id`.

`PARSED_UNCERTAIN=false` is emitted only when correctness, severity, quality, and an explicit `UNCERTAIN=false` all parse successfully. Missing or unrecognized axis values force `PARSED_UNCERTAIN=true`, even when `UNCERTAIN=false` is present.

Duplicate id lines are last-line-wins, matching `vote_for_id`. Callers that assemble TSV rows use the fixed voter-column convention `v1=Claude`, `v2=Codex`, `v3=Cursor`; this parser only parses one file/id pair.

Regression coverage: `skills/design/scripts/test-findings-classification.sh`.
