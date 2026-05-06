# test-false-positive-keywords.sh contract

`scripts/test-false-positive-keywords.sh` is the offline regression harness for `scripts/false-positive-keywords.sh`. The full matcher contract lives in `scripts/false-positive-keywords.md`; this harness sources the production library directly and covers positive fixtures, negative negation/non-overlap fixtures, and helper-failure exit-code propagation. It is wired into `make lint` via the `test-false-positive-keywords` Makefile target and exactly one `test-harnesses-N` shard.
