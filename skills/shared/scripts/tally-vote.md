# tally-vote.sh Contract

`skills/shared/scripts/tally-vote.sh` applies the review voting threshold to parsed ballot findings.

Primary caller: `skills/review/scripts/tally-votes.sh`.

Inputs: `--ballot-file` plus optional `--voter-files`. Voter files are plain text and may contain lines like `FINDING_1 YES` or `FINDING_1 NO`. Stray `EXONERATE` tokens are tolerated and counted as `NO`.

Stdout is `KEY=value` only with per-finding accepted status and YES/NO counts.

Harness: `skills/shared/scripts/test-tally-vote.sh`, wired through `make test-tally-vote`.
