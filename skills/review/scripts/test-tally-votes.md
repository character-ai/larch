# test-tally-votes.sh Contract

Regression harness for `skills/review/scripts/tally-votes.sh`.

It verifies both-down auto-accept behavior, normal two-voter threshold behavior with prewritten vote files, and the 0-voter/1-voter warning accept-all fallbacks. Includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-tally-votes.sh` or `make test-tally-votes`.
