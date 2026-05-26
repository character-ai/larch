# test-tally-plan-review.sh

Regression harness for `tally-plan-review.sh`.

See `tally-plan-review.md` for the full contract. This harness is Makefile-only and is wired through `make test-tally-plan-review`. It keeps the vote-tally and artifact behavior pinned, including degraded / MainAgent paths, explicit `--voter` slot preservation, the default classification TSV path, and the transitional `--voter-files` path. `test-findings-classification.sh` still owns the deeper per-cell forensic TSV parser matrix.
