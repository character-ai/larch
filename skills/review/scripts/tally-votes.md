# tally-votes.sh Contract

`skills/review/scripts/tally-votes.sh` orchestrates review ballot voting.

It redirects `skills/shared/scripts/ballot-parse.sh` output to `$REVIEW_TMPDIR/ballot-parse.env` before reading `FINDING_COUNT`. When `--both-down true`, all findings are auto-accepted and voter launch is skipped. Otherwise it consumes existing `cursor-votes.txt` and `codex-votes.txt` files from the review tmpdir when present. If fewer than two voter files are available, it emits `**⚠ Voting skipped (<N> voter(s) available, minimum 2 required). All findings accepted.**` and accepts every finding; with two voters, it delegates threshold math to `skills/shared/scripts/tally-vote.sh`.

Stdout is normally `KEY=value` only: `ACCEPTED_COUNT`, `REJECTED_COUNT`, `TALLY_FILE`, `ACCEPTED_FINDINGS_FILE`, and `TALLY_OK`. The insufficient-voter fallback also emits the warning to the lib-quiet contract stream (FD 3), as required by `skills/shared/voting-protocol.md`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-tally-votes.sh`, wired through `make test-tally-votes`.
