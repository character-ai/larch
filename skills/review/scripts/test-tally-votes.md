# test-tally-votes.sh Contract

Regression harness for `skills/review/scripts/tally-votes.sh`.

It verifies both-down auto-accept behavior and normal two-voter threshold behavior with prewritten vote files. Includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-tally-votes.sh` or `make test-tally-votes`.
