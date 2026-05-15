# tally-votes.sh Contract

`skills/review/scripts/tally-votes.sh` orchestrates review ballot voting.

It redirects `skills/shared/scripts/ballot-parse.sh` output to `$REVIEW_TMPDIR/ballot-parse.env` before reading `FINDING_COUNT`. When `--both-down true`, all findings are auto-accepted and voter launch is skipped. Otherwise it consumes existing `cursor-votes.txt` and `codex-votes.txt` files from the review tmpdir when present and delegates threshold math to `skills/shared/scripts/tally-vote.sh`.

Stdout is `KEY=value` only: `ACCEPTED_COUNT`, `REJECTED_COUNT`, `TALLY_FILE`, `ACCEPTED_FINDINGS_FILE`, and `TALLY_OK`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-tally-votes.sh`, wired through `make test-tally-votes`.
