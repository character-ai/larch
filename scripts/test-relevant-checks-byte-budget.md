# test-relevant-checks-byte-budget.sh

Purpose: regression-test the green path of `scripts/run-relevant-checks-captured.sh`.

The harness builds a disposable consumer repo with a verbose successful `scripts/relevant-checks.sh`, invokes the helper under a long `${XDG_CACHE_HOME}` path containing spaces, and asserts that stdout stays at or below the fixed 120-byte budget. It also asserts that success stdout contains no `LOG=` or `LOG_FILE=` token and that the captured artifact directory/file modes are `700` and `600` even under `umask 000`.

Primary callers: `make test-relevant-checks-byte-budget` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/run-relevant-checks-captured.sh` and `scripts/run-relevant-checks-captured.md` whenever green-path stdout grammar, tmpdir validation, coverage labels, or artifact modes change.
