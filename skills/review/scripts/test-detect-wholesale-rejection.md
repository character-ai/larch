# test-detect-wholesale-rejection.sh Contract

Regression harness for `skills/review/scripts/detect-wholesale-rejection.sh`.

It verifies the zero-accepted and nonzero-accepted branches, and includes a stdout size cap assertion (≤2 KB).

Run with `bash skills/review/scripts/test-detect-wholesale-rejection.sh` or `make test-detect-wholesale-rejection`.
