# test-tally-plan-review.sh

Regression harness for `tally-plan-review.sh`.

See `tally-plan-review.md` for the full contract. This harness is Makefile-only and is wired through `make test-tally-plan-review`. The forensic TSV contract is covered by `test-findings-classification.sh`; this harness keeps the legacy vote-tally and artifact behavior pinned, including the transitional `--voter-files` path.
