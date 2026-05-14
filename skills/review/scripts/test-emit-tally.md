# test-emit-tally.sh Contract

Regression harness for `skills/review/scripts/emit-tally.sh`.

It verifies markdown summary creation, the `review-summary.json` schema/version/counts, and includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-emit-tally.sh` or `make test-emit-tally`.
